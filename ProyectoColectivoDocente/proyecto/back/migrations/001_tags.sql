-- Ejecutar una sola vez sobre la base existente, sin volver a importar el esquema.
-- Si esta consulta devuelve filas, resolver los códigos duplicados antes del ALTER.
SELECT tag, COUNT(*) AS total
FROM mascotas
WHERE tag IS NOT NULL
GROUP BY tag
HAVING COUNT(*) > 1;

ALTER TABLE mascotas
  ADD COLUMN compartir_contacto BOOLEAN NOT NULL DEFAULT FALSE,
  ADD CONSTRAINT uq_mascotas_tag UNIQUE (tag);
