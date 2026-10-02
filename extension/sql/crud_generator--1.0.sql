-- crud_generator--1.0.sql
-- Generador automatico de procedimientos CRUD de mantenimiento.
-- Ver crud_generator_docs/CONTRACTS.md (S3-4) y DECISIONS.md (ADR-007/009/010/011/013/015)
-- para el contrato formal de esta API.
-- NOTA: este archivo se carga mediante "CREATE EXTENSION crud_generator";
-- no debe ejecutarse directamente con psql -f.

-- ===========================================================================
-- 1. Tipos de datos publicos del resultado
-- ===========================================================================

-- Una fila por columna de la tabla analizada. Ver CONTRACTS.md S3.1.
CREATE TYPE crud_generator.column_meta AS (
  column_name          text,
  data_type            text,
  ordinal_position     integer,
  is_primary_key       boolean,
  pk_position          integer,
  is_nullable          boolean,
  has_default          boolean,
  default_expression   text,
  is_identity          boolean,
  identity_generation  text,
  is_generated         boolean,
  generated_expression text
);

-- Una fila por operacion solicitada a generate_crud. Ver CONTRACTS.md S3.3.
CREATE TYPE crud_generator.generation_result AS (
  operation           text,
  status              text,
  schema_name         text,
  routine_name        text,
  identity_arguments  text,
  message             text,
  sqlstate            text
);

-- ===========================================================================
-- 2. Lectura de catalogos (internas, no forman parte de la API publica)
-- ===========================================================================

CREATE FUNCTION crud_generator._table_oid(p_schema text, p_table text)
RETURNS oid
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  v_oid oid;
BEGIN
  SELECT c.oid INTO v_oid
  FROM pg_catalog.pg_class AS c
  JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
  WHERE n.nspname = p_schema
    AND c.relname = p_table
    AND c.relkind IN ('r', 'p');

  IF v_oid IS NULL THEN
    RAISE EXCEPTION 'La tabla "%"."%" no existe o no es una tabla ordinaria/particionada',
      p_schema, p_table
      USING ERRCODE = '42P01';
  END IF;

  RETURN v_oid;
END;
$$;

COMMENT ON FUNCTION crud_generator._table_oid(text, text) IS
  'Resuelve el oid de una tabla real/particionada; 42P01 si no existe (uso interno).';

-- Metadata completa de columnas de una tabla, en orden ordinal.
-- PK detectada via pg_index.indisprimary; pk_position via ordinalidad de indkey.
CREATE FUNCTION crud_generator._table_columns(p_schema text, p_table text)
RETURNS SETOF crud_generator.column_meta
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  v_oid oid := crud_generator._table_oid(p_schema, p_table);
BEGIN
  RETURN QUERY
  SELECT
    a.attname::text,
    format_type(a.atttypid, a.atttypmod)::text,
    a.attnum::integer,
    (pk.attnum IS NOT NULL),
    pk.pk_position,
    NOT a.attnotnull,
    (a.atthasdef OR a.attidentity <> ''),
    pg_get_expr(d.adbin, d.adrelid)::text,
    (a.attidentity <> ''),
    CASE a.attidentity
      WHEN 'a' THEN 'ALWAYS'
      WHEN 'd' THEN 'BY DEFAULT'
      ELSE NULL
    END,
    (a.attgenerated <> ''),
    CASE WHEN a.attgenerated <> '' THEN pg_get_expr(d.adbin, d.adrelid)::text ELSE NULL END
  FROM pg_catalog.pg_attribute AS a
  LEFT JOIN pg_catalog.pg_attrdef AS d
    ON d.adrelid = a.attrelid AND d.adnum = a.attnum
  LEFT JOIN LATERAL (
    SELECT k.attnum, k.ord::integer AS pk_position
    FROM pg_catalog.pg_index AS i,
         LATERAL unnest(i.indkey::int2[]) WITH ORDINALITY AS k(attnum, ord)
    WHERE i.indrelid = v_oid AND i.indisprimary
  ) AS pk ON pk.attnum = a.attnum
  WHERE a.attrelid = v_oid
    AND a.attnum > 0
    AND NOT a.attisdropped
  ORDER BY a.attnum;
END;
$$;

COMMENT ON FUNCTION crud_generator._table_columns(text, text) IS
  'Metadata completa de columnas en orden ordinal (uso interno; ver analyze_table).';

-- ===========================================================================
-- 3. API publica de analisis (CONTRACTS.md S3.1)
-- ===========================================================================

CREATE FUNCTION crud_generator.analyze_table(schema_name text, table_name text)
RETURNS SETOF crud_generator.column_meta
LANGUAGE sql
STABLE
AS $$
  SELECT * FROM crud_generator._table_columns(schema_name, table_name);
$$;

COMMENT ON FUNCTION crud_generator.analyze_table(text, text) IS
  'Analiza una tabla via catalogos: columnas, tipos, orden, PK (simple/compuesta), '
  'DEFAULT e identity. Objeto inexistente -> error real 42P01 (no una fila de resultado).';

-- ===========================================================================
-- 4. Creacion de procedures con politica de conflicto (ADR-010)
-- ===========================================================================

-- Ejecuta el DDL de creacion, revoca EXECUTE de PUBLIC por defecto (ADR-011)
-- y arma la fila de resultado con la firma real leida del catalogo.
-- 'duplicate_function' (42723) y 'invalid_function_definition' (42P13) se
-- convierten en status='procedure_conflict'; cualquier otro error (permisos,
-- sintaxis, etc.) se propaga tal cual (no se oculta ningun error de PostgreSQL).
CREATE FUNCTION crud_generator._create_procedure(
  p_operation text,
  p_schema    text,
  p_routine   text,
  p_create_sql text
)
RETURNS crud_generator.generation_result
LANGUAGE plpgsql
AS $$
DECLARE
  v_oid oid;
  v_identity_args text;
BEGIN
  EXECUTE p_create_sql;

  SELECT p.oid INTO v_oid
  FROM pg_catalog.pg_proc AS p
  JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
  WHERE n.nspname = p_schema AND p.proname = p_routine
  ORDER BY p.oid DESC
  LIMIT 1;

  v_identity_args := pg_get_function_identity_arguments(v_oid);

  -- Higiene de privilegios: CREATE PROCEDURE otorga EXECUTE a PUBLIC por
  -- defecto; lo revocamos de inmediato (ADR-011). GRANT selectivo queda a
  -- cargo de Python/Joseph sobre la matriz de roles.
  EXECUTE format('REVOKE EXECUTE ON PROCEDURE %s FROM PUBLIC', v_oid::regprocedure);

  RETURN ROW(
    p_operation,
    'success',
    p_schema,
    p_routine,
    v_identity_args,
    format('Procedure %I.%I creado correctamente (EXECUTE revocado de PUBLIC por defecto).', p_schema, p_routine),
    NULL
  )::crud_generator.generation_result;
EXCEPTION
  WHEN duplicate_function THEN
    RETURN ROW(
      p_operation, 'procedure_conflict', p_schema, p_routine, NULL,
      format('Ya existe %I.%I con esa misma firma. Use do_replace=true para reemplazarlo.', p_schema, p_routine),
      SQLSTATE
    )::crud_generator.generation_result;
  WHEN invalid_function_definition THEN
    RETURN ROW(
      p_operation, 'procedure_conflict', p_schema, p_routine, NULL,
      format('Existe un objeto %I.%I que no es un procedure compatible; no se puede reemplazar.', p_schema, p_routine),
      SQLSTATE
    )::crud_generator.generation_result;
END;
$$;

COMMENT ON FUNCTION crud_generator._create_procedure(text, text, text, text) IS
  'Ejecuta CREATE [OR REPLACE] PROCEDURE, revoca EXECUTE de PUBLIC y arma el '
  'resultado estructurado; conflictos conocidos -> procedure_conflict (uso interno).';

-- ===========================================================================
-- 5. Generadores por operacion (uso interno de generate_crud)
--
-- Convencion de nombres de parametro: p_<ordinal_position>. No se usa el
-- nombre de columna para nombrar parametros porque columnas con espacios,
-- acentos o palabras reservadas (ver lab.catalogo_especial) no producirian
-- identificadores PL/pgSQL validos. Los nombres reales de columna solo se
-- usan via quote_ident()/%I al construir el SQL de la tabla.
-- ===========================================================================

-- INSERT: un parametro por columna insertable.
--  * GENERATED ALWAYS (identity o STORED): se omite, no es parametrizable.
--  * GENERATED BY DEFAULT AS IDENTITY: parametro opcional; NULL -> se omite
--    del INSERT (identity autogenera); valor explicito -> OVERRIDING SYSTEM VALUE.
--  * DEFAULT (no identity): parametro opcional; NULL -> se omite del INSERT
--    (aplica el DEFAULT de la tabla). No permite forzar NULL literal en una
--    columna con DEFAULT a traves de este procedure (limitacion documentada,
--    CONTRACTS.md S3.2).
--  * NOT NULL sin default/generada: parametro obligatorio.
--  * Nullable sin default: parametro opcional, NULL se inserta tal cual.
CREATE FUNCTION crud_generator._generate_insert(
  p_schema text,
  p_table  text,
  p_cols   crud_generator.column_meta[],
  p_replace boolean
)
RETURNS crud_generator.generation_result
LANGUAGE plpgsql
AS $$
DECLARE
  v_routine text := p_table || '_insertar';
  v_col crud_generator.column_meta;
  v_param_name text;
  -- Postgres exige que todo parametro CON DEFAULT venga despues de todos los
  -- que no tienen DEFAULT. El orden ordinal de la tabla no garantiza eso (una
  -- columna con DEFAULT puede ir antes que una NOT NULL sin DEFAULT), asi que
  -- se acumulan en dos listas separadas y se concatenan al final: primero los
  -- obligatorios (sin DEFAULT), despues los opcionales (con DEFAULT NULL).
  v_required_params text[] := ARRAY[]::text[];
  v_required_lines  text[] := ARRAY[]::text[];
  v_optional_params text[] := ARRAY[]::text[];
  v_optional_lines  text[] := ARRAY[]::text[];
  v_params text[];
  v_lines  text[];
  v_body text;
  v_create_sql text;
BEGIN
  FOREACH v_col IN ARRAY p_cols LOOP
    IF v_col.is_generated THEN
      CONTINUE;
    END IF;
    IF v_col.is_identity AND v_col.identity_generation = 'ALWAYS' THEN
      CONTINUE;
    END IF;

    v_param_name := format('p_%s', v_col.ordinal_position);

    IF v_col.is_identity AND v_col.identity_generation = 'BY DEFAULT' THEN
      -- Opcional con reemplazo por generador: NULL -> se omite (identity
      -- autogenera); valor explicito -> OVERRIDING SYSTEM VALUE.
      v_optional_params := v_optional_params || format('%I %s DEFAULT NULL', v_param_name, v_col.data_type);
      v_optional_lines := v_optional_lines || format(
        '  IF %I IS NOT NULL THEN v_cols := v_cols || quote_ident(%L); v_vals := v_vals || quote_nullable(%I); v_override := true; END IF;',
        v_param_name, v_col.column_name, v_param_name
      );
    ELSIF v_col.has_default THEN
      -- Opcional con reemplazo por DEFAULT de tabla: NULL -> se omite.
      v_optional_params := v_optional_params || format('%I %s DEFAULT NULL', v_param_name, v_col.data_type);
      v_optional_lines := v_optional_lines || format(
        '  IF %I IS NOT NULL THEN v_cols := v_cols || quote_ident(%L); v_vals := v_vals || quote_nullable(%I); END IF;',
        v_param_name, v_col.column_name, v_param_name
      );
    ELSIF v_col.is_nullable THEN
      -- Opcional sin DEFAULT de tabla: siempre se incluye la columna (con
      -- NULL si no se indica valor), no hay DEFAULT al que recurrir.
      v_optional_params := v_optional_params || format('%I %s DEFAULT NULL', v_param_name, v_col.data_type);
      v_optional_lines := v_optional_lines || format(
        '  v_cols := v_cols || quote_ident(%L); v_vals := v_vals || quote_nullable(%I);',
        v_col.column_name, v_param_name
      );
    ELSE
      -- Obligatorio: NOT NULL sin DEFAULT ni generacion.
      v_required_params := v_required_params || format('%I %s', v_param_name, v_col.data_type);
      v_required_lines := v_required_lines || format(
        '  v_cols := v_cols || quote_ident(%L); v_vals := v_vals || quote_nullable(%I);',
        v_col.column_name, v_param_name
      );
    END IF;
  END LOOP;

  v_params := v_required_params || v_optional_params;
  v_lines := v_required_lines || v_optional_lines;

  IF array_length(v_params, 1) IS NULL THEN
    v_body := format($f$
BEGIN
  EXECUTE format('INSERT INTO %%I.%%I DEFAULT VALUES', %L, %L);
END;
$f$, p_schema, p_table);
  ELSE
    v_body := format($f$
DECLARE
  v_cols text[] := ARRAY[]::text[];
  v_vals text[] := ARRAY[]::text[];
  v_override boolean := false;
BEGIN
%s
  IF array_length(v_cols, 1) IS NULL THEN
    EXECUTE format('INSERT INTO %%I.%%I DEFAULT VALUES', %L, %L);
  ELSE
    EXECUTE format('INSERT INTO %%I.%%I (%%s) %%s VALUES (%%s)',
      %L, %L, array_to_string(v_cols, ', '),
      CASE WHEN v_override THEN 'OVERRIDING SYSTEM VALUE' ELSE '' END,
      array_to_string(v_vals, ', '));
  END IF;
END;
$f$, array_to_string(v_lines, E'\n'), p_schema, p_table, p_schema, p_table);
  END IF;

  v_create_sql := format(
    'CREATE %s PROCEDURE %I.%I(%s) LANGUAGE plpgsql SECURITY INVOKER SET search_path = %I, pg_temp AS %L',
    CASE WHEN p_replace THEN 'OR REPLACE' ELSE '' END,
    p_schema, v_routine, array_to_string(v_params, ', '), p_schema, v_body
  );

  RETURN crud_generator._create_procedure('INSERT', p_schema, v_routine, v_create_sql);
END;
$$;

-- READ:
--  * Con PK: consultar(INOUT pk..., INOUT resto...) por PK completa, una fila.
--    Fila inexistente -> SQLSTATE P0002 (ADR-015).
--  * Sin PK: consultar(OUT resultado refcursor) con listado completo (ADR-009).
CREATE FUNCTION crud_generator._generate_read(
  p_schema text,
  p_table  text,
  p_pk     crud_generator.column_meta[],
  p_nonpk  crud_generator.column_meta[],
  p_replace boolean
)
RETURNS crud_generator.generation_result
LANGUAGE plpgsql
AS $$
DECLARE
  v_routine text := p_table || '_consultar';
  v_col crud_generator.column_meta;
  v_param_name text;
  v_params text[] := ARRAY[]::text[];
  v_where  text[] := ARRAY[]::text[];
  v_select_cols text[] := ARRAY[]::text[];
  v_into_vars   text[] := ARRAY[]::text[];
  v_all crud_generator.column_meta[];
  v_body text;
  v_create_sql text;
BEGIN
  IF p_pk IS NULL OR array_length(p_pk, 1) IS NULL THEN
    v_body := format($f$
BEGIN
  OPEN resultado FOR EXECUTE format('SELECT * FROM %%I.%%I', %L, %L);
END;
$f$, p_schema, p_table);

    v_create_sql := format(
      'CREATE %s PROCEDURE %I.%I(OUT resultado refcursor) LANGUAGE plpgsql SECURITY INVOKER SET search_path = %I, pg_temp AS %L',
      CASE WHEN p_replace THEN 'OR REPLACE' ELSE '' END, p_schema, v_routine, p_schema, v_body
    );

    RETURN crud_generator._create_procedure('READ', p_schema, v_routine, v_create_sql);
  END IF;

  FOREACH v_col IN ARRAY p_pk LOOP
    v_param_name := format('p_%s', v_col.ordinal_position);
    v_params := v_params || format('INOUT %I %s DEFAULT NULL', v_param_name, v_col.data_type);
    v_where := v_where || format('%I = %I', v_col.column_name, v_param_name);
  END LOOP;

  FOREACH v_col IN ARRAY p_nonpk LOOP
    v_param_name := format('p_%s', v_col.ordinal_position);
    v_params := v_params || format('INOUT %I %s DEFAULT NULL', v_param_name, v_col.data_type);
  END LOOP;

  v_all := p_pk || p_nonpk;
  FOREACH v_col IN ARRAY v_all LOOP
    v_select_cols := v_select_cols || quote_ident(v_col.column_name);
    v_into_vars := v_into_vars || format('p_%s', v_col.ordinal_position);
  END LOOP;

  v_body := format($f$
BEGIN
  SELECT %s INTO %s FROM %I.%I WHERE %s;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'No existe fila en %s con la clave primaria indicada' USING ERRCODE = 'P0002';
  END IF;
END;
$f$,
    array_to_string(v_select_cols, ', '),
    array_to_string(v_into_vars, ', '),
    p_schema, p_table,
    array_to_string(v_where, ' AND '),
    p_schema || '.' || p_table
  );

  v_create_sql := format(
    'CREATE %s PROCEDURE %I.%I(%s) LANGUAGE plpgsql SECURITY INVOKER SET search_path = %I, pg_temp AS %L',
    CASE WHEN p_replace THEN 'OR REPLACE' ELSE '' END, p_schema, v_routine, array_to_string(v_params, ', '), p_schema, v_body
  );

  RETURN crud_generator._create_procedure('READ', p_schema, v_routine, v_create_sql);
END;
$$;

-- UPDATE: solo si hay PK (si no, not_applicable, ADR-009). IN pk..., IN resto
-- actualizable (se excluyen columnas GENERATED ALWAYS STORED). Fila
-- inexistente -> P0002.
CREATE FUNCTION crud_generator._generate_update(
  p_schema text,
  p_table  text,
  p_pk     crud_generator.column_meta[],
  p_nonpk  crud_generator.column_meta[],
  p_replace boolean
)
RETURNS crud_generator.generation_result
LANGUAGE plpgsql
AS $$
DECLARE
  v_routine text := p_table || '_actualizar';
  v_col crud_generator.column_meta;
  v_param_name text;
  v_params text[] := ARRAY[]::text[];
  v_where  text[] := ARRAY[]::text[];
  v_set    text[] := ARRAY[]::text[];
  v_body text;
  v_create_sql text;
BEGIN
  IF p_pk IS NULL OR array_length(p_pk, 1) IS NULL THEN
    RETURN ROW(
      'UPDATE', 'not_applicable', p_schema, NULL, NULL,
      format('%I.%I no tiene clave primaria; UPDATE generico no aplica (ADR-009).', p_schema, p_table),
      NULL
    )::crud_generator.generation_result;
  END IF;

  FOREACH v_col IN ARRAY p_pk LOOP
    v_param_name := format('p_%s', v_col.ordinal_position);
    v_params := v_params || format('%I %s', v_param_name, v_col.data_type);
    v_where := v_where || format('%I = %I', v_col.column_name, v_param_name);
  END LOOP;

  FOREACH v_col IN ARRAY p_nonpk LOOP
    IF v_col.is_generated THEN
      CONTINUE;
    END IF;
    v_param_name := format('p_%s', v_col.ordinal_position);
    v_params := v_params || format('%I %s', v_param_name, v_col.data_type);
    v_set := v_set || format('%I = %I', v_col.column_name, v_param_name);
  END LOOP;

  IF array_length(v_set, 1) IS NULL THEN
    RETURN ROW(
      'UPDATE', 'not_applicable', p_schema, NULL, NULL,
      format('%I.%I no tiene columnas actualizables fuera de la clave primaria.', p_schema, p_table),
      NULL
    )::crud_generator.generation_result;
  END IF;

  v_body := format($f$
BEGIN
  UPDATE %I.%I SET %s WHERE %s;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'No existe fila en %s con la clave primaria indicada' USING ERRCODE = 'P0002';
  END IF;
END;
$f$, p_schema, p_table, array_to_string(v_set, ', '), array_to_string(v_where, ' AND '), p_schema || '.' || p_table);

  v_create_sql := format(
    'CREATE %s PROCEDURE %I.%I(%s) LANGUAGE plpgsql SECURITY INVOKER SET search_path = %I, pg_temp AS %L',
    CASE WHEN p_replace THEN 'OR REPLACE' ELSE '' END, p_schema, v_routine, array_to_string(v_params, ', '), p_schema, v_body
  );

  RETURN crud_generator._create_procedure('UPDATE', p_schema, v_routine, v_create_sql);
END;
$$;

-- DELETE: solo si hay PK (si no, not_applicable, ADR-009). IN pk...
-- Fila inexistente -> P0002.
CREATE FUNCTION crud_generator._generate_delete(
  p_schema text,
  p_table  text,
  p_pk     crud_generator.column_meta[],
  p_replace boolean
)
RETURNS crud_generator.generation_result
LANGUAGE plpgsql
AS $$
DECLARE
  v_routine text := p_table || '_eliminar';
  v_col crud_generator.column_meta;
  v_param_name text;
  v_params text[] := ARRAY[]::text[];
  v_where  text[] := ARRAY[]::text[];
  v_body text;
  v_create_sql text;
BEGIN
  IF p_pk IS NULL OR array_length(p_pk, 1) IS NULL THEN
    RETURN ROW(
      'DELETE', 'not_applicable', p_schema, NULL, NULL,
      format('%I.%I no tiene clave primaria; DELETE generico no aplica (ADR-009).', p_schema, p_table),
      NULL
    )::crud_generator.generation_result;
  END IF;

  FOREACH v_col IN ARRAY p_pk LOOP
    v_param_name := format('p_%s', v_col.ordinal_position);
    v_params := v_params || format('%I %s', v_param_name, v_col.data_type);
    v_where := v_where || format('%I = %I', v_col.column_name, v_param_name);
  END LOOP;

  v_body := format($f$
BEGIN
  DELETE FROM %I.%I WHERE %s;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'No existe fila en %s con la clave primaria indicada' USING ERRCODE = 'P0002';
  END IF;
END;
$f$, p_schema, p_table, array_to_string(v_where, ' AND '), p_schema || '.' || p_table);

  v_create_sql := format(
    'CREATE %s PROCEDURE %I.%I(%s) LANGUAGE plpgsql SECURITY INVOKER SET search_path = %I, pg_temp AS %L',
    CASE WHEN p_replace THEN 'OR REPLACE' ELSE '' END, p_schema, v_routine, array_to_string(v_params, ', '), p_schema, v_body
  );

  RETURN crud_generator._create_procedure('DELETE', p_schema, v_routine, v_create_sql);
END;
$$;

-- ===========================================================================
-- 6. API publica de generacion (CONTRACTS.md S3.2)
-- ===========================================================================

CREATE FUNCTION crud_generator.generate_crud(
  schema_name text,
  table_name  text,
  operations  text[],
  do_replace  boolean DEFAULT false
)
RETURNS SETOF crud_generator.generation_result
LANGUAGE plpgsql
AS $$
DECLARE
  v_valid_ops text[] := ARRAY['INSERT', 'READ', 'UPDATE', 'DELETE'];
  v_op text;
  v_cols crud_generator.column_meta[];
  v_pk crud_generator.column_meta[];
  v_nonpk crud_generator.column_meta[];
  v_result crud_generator.generation_result;
BEGIN
  -- operations vacío/nulo → fila validation_error (CONTRACTS.md §3.3),
  -- no excepción: Python distingue el caso sin parsear SQLSTATE.
  IF operations IS NULL OR array_length(operations, 1) IS NULL THEN
    RETURN NEXT ROW(NULL, 'validation_error', schema_name, NULL, NULL,
      'Debe indicar al menos una operacion (INSERT/READ/UPDATE/DELETE).', NULL)
      ::crud_generator.generation_result;
    RETURN;
  END IF;

  -- Valida existencia de la tabla (42P01 si no existe, error real, no fila).
  PERFORM crud_generator._table_oid(schema_name, table_name);

  SELECT array_agg(c ORDER BY c.ordinal_position)
    INTO v_cols
    FROM crud_generator._table_columns(schema_name, table_name) AS c;

  SELECT array_agg(c ORDER BY c.pk_position)
    INTO v_pk
    FROM unnest(v_cols) AS c
    WHERE c.is_primary_key;

  SELECT array_agg(c ORDER BY c.ordinal_position)
    INTO v_nonpk
    FROM unnest(v_cols) AS c
    WHERE NOT c.is_primary_key;

  FOREACH v_op IN ARRAY operations LOOP
    IF v_op IS NULL THEN
      RETURN NEXT ROW(NULL, 'validation_error', schema_name, NULL, NULL,
        'Operacion NULL no es valida.', NULL)::crud_generator.generation_result;
      CONTINUE;
    END IF;

    v_op := upper(v_op);

    IF NOT (v_op = ANY (v_valid_ops)) THEN
      RETURN NEXT ROW(v_op, 'validation_error', schema_name, NULL, NULL,
        format('Operacion desconocida: %s (use INSERT/READ/UPDATE/DELETE).', v_op), NULL)
        ::crud_generator.generation_result;
      CONTINUE;
    END IF;

    CASE v_op
      WHEN 'INSERT' THEN
        v_result := crud_generator._generate_insert(schema_name, table_name, v_cols, do_replace);
      WHEN 'READ' THEN
        v_result := crud_generator._generate_read(schema_name, table_name, v_pk, v_nonpk, do_replace);
      WHEN 'UPDATE' THEN
        v_result := crud_generator._generate_update(schema_name, table_name, v_pk, v_nonpk, do_replace);
      WHEN 'DELETE' THEN
        v_result := crud_generator._generate_delete(schema_name, table_name, v_pk, do_replace);
    END CASE;

    RETURN NEXT v_result;
  END LOOP;

  RETURN;
END;
$$;

COMMENT ON FUNCTION crud_generator.generate_crud(text, text, text[], boolean) IS
  'Genera los procedures CRUD solicitados para schema_name.table_name. '
  'Requiere que el rol que ejecuta tenga CREATE sobre schema_name (ej. crud_admin, '
  'ADR-011); el objeto creado queda con ese rol como owner. Tabla inexistente '
  '-> error real 42P01. Ver CONTRACTS.md S3 para el significado de cada status.';
