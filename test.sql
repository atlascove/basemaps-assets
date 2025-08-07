LOAD 'spatial';
LOAD 's3';
LOAD 'postgres';

-- List all SVG files in the icons directory and remove the .svg extension
CREATE TABLE files AS (
  SELECT REGEXP_REPLACE(file, '.*/([^/]*)\.svg', '\1') AS icon_name
  FROM glob(
      '/Users/nguyencuong/Desktop/Fotoshi/sources/basemaps-assets/icons/*.svg'
    )
);


CREATE OR REPLACE SECRET postgres_secret (
    TYPE postgres,
    PROVIDER config,
    HOST 'localhost',
    PORT 5432,
    DATABASE 'fotoshi_dev',
    USER 'super_fotoshi',
    PASSWORD 'G7k9q2z8L1m4v6s3'
  );
ATTACH '' AS pg (TYPE POSTGRES, SECRET postgres_secret);


SHOW ALL TABLES;

SELECT DISTINCT icon FROM pg.presets;

-- filter icon has in pg.presets but not in files
SELECT DISTINCT icon FROM pg.presets
WHERE icon NOT IN (SELECT icon_name FROM files);

-- export csv
COPY (SELECT DISTINCT icon FROM pg.presets
WHERE icon NOT IN (SELECT icon_name FROM files))
TO 'missing_icons.csv'
WITH (FORMAT CSV, HEADER);

-- filter icon has in files but not in pg.presets
SELECT icon_name FROM files
WHERE icon_name NOT IN (SELECT icon FROM pg.presets);