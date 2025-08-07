#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { DOMParser } = require('xmldom');

const iconsDir = path.join(__dirname, 'icons');

function extractCoordinatesFromPath(pathData) {
  if (!pathData) return { minX: 0, minY: 0, maxX: 0, maxY: 0 };

  const coords = [];
  const matches = pathData.match(/[-+]?[0-9]*\.?[0-9]+/g);
  
  if (matches) {
    for (let i = 0; i < matches.length; i += 2) {
      const x = parseFloat(matches[i]);
      const y = parseFloat(matches[i + 1]);
      if (!isNaN(x) && !isNaN(y)) {
        coords.push({ x, y });
      }
    }
  }

  if (coords.length === 0) return { minX: 0, minY: 0, maxX: 0, maxY: 0 };

  const minX = Math.min(...coords.map(c => c.x));
  const minY = Math.min(...coords.map(c => c.y));
  const maxX = Math.max(...coords.map(c => c.x));
  const maxY = Math.max(...coords.map(c => c.y));

  return { minX, minY, maxX, maxY };
}

function analyzeSvgFile(filePath) {
  const fileName = path.basename(filePath);
  const results = {
    fileName,
    filePath,
    errors: []
  };

  try {
    const content = fs.readFileSync(filePath, 'utf8');
    
    // Basic file checks
    if (!content || content.trim().length === 0) {
      results.errors.push({ type: 'EMPTY_FILE', detail: 'File is empty' });
      return results;
    }

    if (content.length < 50) {
      results.errors.push({ type: 'SHORT_CONTENT', detail: 'File content is suspiciously short' });
    }

    if (!content.includes('<svg')) {
      results.errors.push({ type: 'MISSING_SVG_TAG', detail: 'Missing <svg> tag' });
      return results;
    }

    // Parse XML
    const parser = new DOMParser({
      errorHandler: {
        warning: (msg) => results.errors.push({ type: 'XML_WARNING', detail: msg }),
        error: (msg) => results.errors.push({ type: 'XML_ERROR', detail: msg }),
        fatalError: (msg) => results.errors.push({ type: 'XML_FATAL_ERROR', detail: msg })
      }
    });

    const doc = parser.parseFromString(content, 'text/xml');
    
    if (!doc) {
      results.errors.push({ type: 'XML_PARSE_FAILED', detail: 'Failed to parse XML' });
      return results;
    }

    const svgElement = doc.getElementsByTagName('svg')[0];
    if (!svgElement) {
      results.errors.push({ type: 'NO_SVG_ELEMENT', detail: 'No SVG element found' });
      return results;
    }

    // Check for drawable content
    const hasPath = svgElement.getElementsByTagName('path').length > 0;
    const hasCircle = svgElement.getElementsByTagName('circle').length > 0;
    const hasRect = svgElement.getElementsByTagName('rect').length > 0;
    const hasPolygon = svgElement.getElementsByTagName('polygon').length > 0;
    const hasLine = svgElement.getElementsByTagName('line').length > 0;
    const hasG = svgElement.getElementsByTagName('g').length > 0;

    if (!hasPath && !hasCircle && !hasRect && !hasPolygon && !hasLine && !hasG) {
      results.errors.push({ type: 'NO_DRAWABLE_CONTENT', detail: 'SVG appears to have no drawable content' });
    }

    // Check dimensions
    const viewBox = svgElement.getAttribute('viewBox');
    const width = svgElement.getAttribute('width');
    const height = svgElement.getAttribute('height');

    if (!viewBox && (!width || !height)) {
      results.errors.push({ type: 'NO_DIMENSIONS', detail: 'SVG has no viewBox or dimensions specified' });
    }

    // ViewBox mismatch analysis
    if (viewBox) {
      const viewBoxParts = viewBox.split(/\s+/).map(parseFloat);
      if (viewBoxParts.length !== 4) {
        results.errors.push({ type: 'INVALID_VIEWBOX_FORMAT', detail: 'Invalid viewBox format' });
      } else {
        const [vbMinX, vbMinY, vbWidth, vbHeight] = viewBoxParts;
        const vbMaxX = vbMinX + vbWidth;
        const vbMaxY = vbMinY + vbHeight;

        // Analyze path coordinates
        const pathElements = svgElement.getElementsByTagName('path');
        let globalMinX = Infinity, globalMinY = Infinity;
        let globalMaxX = -Infinity, globalMaxY = -Infinity;
        let hasValidPaths = false;

        for (let i = 0; i < pathElements.length; i++) {
          const pathData = pathElements[i].getAttribute('d');
          if (pathData) {
            const bounds = extractCoordinatesFromPath(pathData);
            if (bounds.minX !== bounds.maxX || bounds.minY !== bounds.maxY) {
              globalMinX = Math.min(globalMinX, bounds.minX);
              globalMinY = Math.min(globalMinY, bounds.minY);
              globalMaxX = Math.max(globalMaxX, bounds.maxX);
              globalMaxY = Math.max(globalMaxY, bounds.maxY);
              hasValidPaths = true;
            }
          }
        }

        // Check other shape elements
        const otherElements = ['circle', 'rect', 'ellipse', 'line', 'polygon', 'polyline'];
        otherElements.forEach(tagName => {
          const elements = svgElement.getElementsByTagName(tagName);
          for (let i = 0; i < elements.length; i++) {
            const element = elements[i];
            let x = 0, y = 0, w = 0, h = 0;

            switch (tagName) {
              case 'circle':
                const cx = parseFloat(element.getAttribute('cx') || 0);
                const cy = parseFloat(element.getAttribute('cy') || 0);
                const r = parseFloat(element.getAttribute('r') || 0);
                x = cx - r; y = cy - r; w = r * 2; h = r * 2;
                break;
              case 'rect':
                x = parseFloat(element.getAttribute('x') || 0);
                y = parseFloat(element.getAttribute('y') || 0);
                w = parseFloat(element.getAttribute('width') || 0);
                h = parseFloat(element.getAttribute('height') || 0);
                break;
              case 'ellipse':
                const ecx = parseFloat(element.getAttribute('cx') || 0);
                const ecy = parseFloat(element.getAttribute('cy') || 0);
                const rx = parseFloat(element.getAttribute('rx') || 0);
                const ry = parseFloat(element.getAttribute('ry') || 0);
                x = ecx - rx; y = ecy - ry; w = rx * 2; h = ry * 2;
                break;
            }

            if (w > 0 || h > 0) {
              globalMinX = Math.min(globalMinX, x);
              globalMinY = Math.min(globalMinY, y);
              globalMaxX = Math.max(globalMaxX, x + w);
              globalMaxY = Math.max(globalMaxY, y + h);
              hasValidPaths = true;
            }
          }
        });

        if (hasValidPaths) {
          // Check for viewBox mismatch with tolerance
          const tolerance = 5;
          const pathOutsideViewBox = 
            globalMaxX > vbMaxX + tolerance ||
            globalMaxY > vbMaxY + tolerance ||
            globalMinX < vbMinX - tolerance ||
            globalMinY < vbMinY - tolerance;

          if (pathOutsideViewBox) {
            results.errors.push({
              type: 'VIEWBOX_MISMATCH',
              detail: `Path coordinates (${globalMinX.toFixed(1)}, ${globalMinY.toFixed(1)}) to (${globalMaxX.toFixed(1)}, ${globalMaxY.toFixed(1)}) extend outside viewBox (${vbMinX}, ${vbMinY}) to (${vbMaxX}, ${vbMaxY})`
            });
          }

          // Check if viewBox is much larger than needed
          const pathWidth = globalMaxX - globalMinX;
          const pathHeight = globalMaxY - globalMinY;
          const viewBoxWaste = (vbWidth * vbHeight) / (pathWidth * pathHeight);
          
          if (viewBoxWaste > 10 && (vbWidth > pathWidth * 2 || vbHeight > pathHeight * 2)) {
            results.errors.push({
              type: 'VIEWBOX_TOO_LARGE',
              detail: `ViewBox is much larger than needed - viewBox: ${vbWidth}x${vbHeight}, content: ${pathWidth.toFixed(1)}x${pathHeight.toFixed(1)}`
            });
          }
        }
      }
    }

  } catch (error) {
    results.errors.push({ type: 'EXCEPTION', detail: `Exception: ${error.message}` });
  }

  return results;
}

function exportToCsv(results, outputPath) {
  const csvRows = ['Filename,Error Type,Detail'];
  
  results.forEach(result => {
    if (result.errors.length === 0) {
      csvRows.push(`"${result.fileName}","VALID","No issues found"`);
    } else {
      result.errors.forEach(error => {
        const escapedDetail = error.detail.replace(/"/g, '""');
        csvRows.push(`"${result.fileName}","${error.type}","${escapedDetail}"`);
      });
    }
  });

  fs.writeFileSync(outputPath, csvRows.join('\n'), 'utf8');
}

function main() {
  console.log('🔍 Analyzing SVG files for all issues...\n');
  
  if (!fs.existsSync(iconsDir)) {
    console.error(`❌ Icons directory not found: ${iconsDir}`);
    process.exit(1);
  }

  const svgFiles = fs.readdirSync(iconsDir)
    .filter(file => file.endsWith('.svg'))
    .map(file => path.join(iconsDir, file));

  console.log(`Found ${svgFiles.length} SVG files\n`);

  const results = svgFiles.map(analyzeSvgFile);
  
  const problematicFiles = results.filter(result => result.errors.length > 0);
  const validFiles = results.filter(result => result.errors.length === 0);

  console.log(`📊 Results:`);
  console.log(`  ✅ Valid files: ${validFiles.length}`);
  console.log(`  ❌ Files with issues: ${problematicFiles.length}`);

  // Count error types
  const errorCounts = {};
  results.forEach(result => {
    result.errors.forEach(error => {
      errorCounts[error.type] = (errorCounts[error.type] || 0) + 1;
    });
  });

  if (Object.keys(errorCounts).length > 0) {
    console.log('\n📋 Error Type Summary:');
    Object.entries(errorCounts)
      .sort((a, b) => b[1] - a[1])
      .forEach(([type, count]) => {
        console.log(`  ${type}: ${count}`);
      });
  }

  // Export to CSV
  const csvPath = path.join(__dirname, 'svg-analysis-report.csv');
  exportToCsv(results, csvPath);
  console.log(`\n📄 CSV report exported to: ${csvPath}`);

  if (problematicFiles.length > 0) {
    console.log(`\n📝 Summary: ${problematicFiles.length} files have issues out of ${svgFiles.length} total SVG files`);
  } else {
    console.log('\n🎉 All SVG files are valid!');
  }
}

if (require.main === module) {
  main();
}

module.exports = { analyzeSvgFile, exportToCsv };