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

function calculateContentBounds(svgElement) {
  let globalMinX = Infinity, globalMinY = Infinity;
  let globalMaxX = -Infinity, globalMaxY = -Infinity;
  let hasContent = false;

  // Analyze path elements
  const pathElements = svgElement.getElementsByTagName('path');
  for (let i = 0; i < pathElements.length; i++) {
    const pathData = pathElements[i].getAttribute('d');
    if (pathData) {
      const bounds = extractCoordinatesFromPath(pathData);
      if (bounds.minX !== bounds.maxX || bounds.minY !== bounds.maxY) {
        globalMinX = Math.min(globalMinX, bounds.minX);
        globalMinY = Math.min(globalMinY, bounds.minY);
        globalMaxX = Math.max(globalMaxX, bounds.maxX);
        globalMaxY = Math.max(globalMaxY, bounds.maxY);
        hasContent = true;
      }
    }
  }

  // Analyze other shape elements
  const otherElements = ['circle', 'rect', 'ellipse', 'line', 'polygon', 'polyline'];
  otherElements.forEach(tagName => {
    const elements = svgElement.getElementsByTagName(tagName);
    for (let i = 0; i < elements.length; i++) {
      const element = elements[i];
      let x = 0, y = 0, width = 0, height = 0;

      switch (tagName) {
        case 'circle':
          const cx = parseFloat(element.getAttribute('cx') || 0);
          const cy = parseFloat(element.getAttribute('cy') || 0);
          const r = parseFloat(element.getAttribute('r') || 0);
          x = cx - r; y = cy - r; width = r * 2; height = r * 2;
          break;
        case 'rect':
          x = parseFloat(element.getAttribute('x') || 0);
          y = parseFloat(element.getAttribute('y') || 0);
          width = parseFloat(element.getAttribute('width') || 0);
          height = parseFloat(element.getAttribute('height') || 0);
          break;
        case 'ellipse':
          const ecx = parseFloat(element.getAttribute('cx') || 0);
          const ecy = parseFloat(element.getAttribute('cy') || 0);
          const rx = parseFloat(element.getAttribute('rx') || 0);
          const ry = parseFloat(element.getAttribute('ry') || 0);
          x = ecx - rx; y = ecy - ry; width = rx * 2; height = ry * 2;
          break;
        case 'line':
          const x1 = parseFloat(element.getAttribute('x1') || 0);
          const y1 = parseFloat(element.getAttribute('y1') || 0);
          const x2 = parseFloat(element.getAttribute('x2') || 0);
          const y2 = parseFloat(element.getAttribute('y2') || 0);
          x = Math.min(x1, x2); y = Math.min(y1, y2);
          width = Math.abs(x2 - x1); height = Math.abs(y2 - y1);
          break;
        case 'polygon':
        case 'polyline':
          const points = element.getAttribute('points');
          if (points) {
            const coords = points.trim().split(/[\s,]+/).map(parseFloat);
            for (let j = 0; j < coords.length; j += 2) {
              if (!isNaN(coords[j]) && !isNaN(coords[j + 1])) {
                globalMinX = Math.min(globalMinX, coords[j]);
                globalMinY = Math.min(globalMinY, coords[j + 1]);
                globalMaxX = Math.max(globalMaxX, coords[j]);
                globalMaxY = Math.max(globalMaxY, coords[j + 1]);
                hasContent = true;
              }
            }
          }
          continue;
      }

      if (width > 0 || height > 0) {
        globalMinX = Math.min(globalMinX, x);
        globalMinY = Math.min(globalMinY, y);
        globalMaxX = Math.max(globalMaxX, x + width);
        globalMaxY = Math.max(globalMaxY, y + height);
        hasContent = true;
      }
    }
  });

  if (!hasContent) {
    return null;
  }

  return { minX: globalMinX, minY: globalMinY, maxX: globalMaxX, maxY: globalMaxY };
}

function fixSvgFile(filePath, dryRun = false) {
  const fileName = path.basename(filePath);
  const result = {
    fileName,
    filePath,
    fixed: false,
    changes: [],
    errors: []
  };

  try {
    const content = fs.readFileSync(filePath, 'utf8');
    
    if (!content || content.trim().length === 0) {
      result.errors.push('File is empty - cannot fix');
      return result;
    }

    if (!content.includes('<svg')) {
      result.errors.push('Missing <svg> tag - cannot fix');
      return result;
    }

    const parser = new DOMParser({
      errorHandler: {
        warning: () => {},
        error: () => {},
        fatalError: () => {}
      }
    });

    const doc = parser.parseFromString(content, 'text/xml');
    const svgElement = doc.getElementsByTagName('svg')[0];
    
    if (!svgElement) {
      result.errors.push('No SVG element found - cannot fix');
      return result;
    }

    // Calculate content bounds
    const contentBounds = calculateContentBounds(svgElement);
    if (!contentBounds) {
      result.errors.push('No drawable content found - cannot determine proper viewBox');
      return result;
    }

    const viewBoxAttr = svgElement.getAttribute('viewBox');
    let needsFix = false;
    let newViewBox = null;

    if (!viewBoxAttr) {
      // Add missing viewBox
      const padding = 10; // Add some padding
      const minX = Math.floor(contentBounds.minX - padding);
      const minY = Math.floor(contentBounds.minY - padding);
      const width = Math.ceil(contentBounds.maxX - contentBounds.minX + padding * 2);
      const height = Math.ceil(contentBounds.maxY - contentBounds.minY + padding * 2);
      
      newViewBox = `${minX} ${minY} ${width} ${height}`;
      needsFix = true;
      result.changes.push(`Added missing viewBox: "${newViewBox}"`);
    } else {
      // Check existing viewBox
      const viewBoxParts = viewBoxAttr.split(/\s+/).map(parseFloat);
      if (viewBoxParts.length !== 4) {
        result.errors.push('Invalid viewBox format - cannot fix');
        return result;
      }

      const [vbMinX, vbMinY, vbWidth, vbHeight] = viewBoxParts;
      const vbMaxX = vbMinX + vbWidth;
      const vbMaxY = vbMinY + vbHeight;

      // Check if content extends outside viewBox
      const tolerance = 5;
      const contentOutside = 
        contentBounds.maxX > vbMaxX + tolerance ||
        contentBounds.maxY > vbMaxY + tolerance ||
        contentBounds.minX < vbMinX - tolerance ||
        contentBounds.minY < vbMinY - tolerance;

      if (contentOutside) {
        // Calculate new viewBox that encompasses all content
        const padding = Math.max(10, Math.min(vbWidth, vbHeight) * 0.05); // 5% padding or 10px minimum
        const minX = Math.floor(Math.min(vbMinX, contentBounds.minX - padding));
        const minY = Math.floor(Math.min(vbMinY, contentBounds.minY - padding));
        const maxX = Math.ceil(Math.max(vbMaxX, contentBounds.maxX + padding));
        const maxY = Math.ceil(Math.max(vbMaxY, contentBounds.maxY + padding));
        
        const width = maxX - minX;
        const height = maxY - minY;
        
        newViewBox = `${minX} ${minY} ${width} ${height}`;
        needsFix = true;
        result.changes.push(`Fixed viewBox mismatch: "${viewBoxAttr}" → "${newViewBox}"`);
        result.changes.push(`Content bounds: (${contentBounds.minX.toFixed(1)}, ${contentBounds.minY.toFixed(1)}) to (${contentBounds.maxX.toFixed(1)}, ${contentBounds.maxY.toFixed(1)})`);
      }
    }

    if (needsFix && !dryRun) {
      // Apply the fix by modifying the file content
      let newContent = content;
      
      if (!viewBoxAttr) {
        // Add viewBox attribute
        newContent = newContent.replace(
          /<svg([^>]*)>/,
          `<svg$1 viewBox="${newViewBox}">`
        );
      } else {
        // Replace existing viewBox
        newContent = newContent.replace(
          new RegExp(`viewBox\\s*=\\s*["'][^"']*["']`, 'i'),
          `viewBox="${newViewBox}"`
        );
      }

      fs.writeFileSync(filePath, newContent, 'utf8');
      result.fixed = true;
    } else if (needsFix) {
      result.fixed = true; // Would be fixed in non-dry-run mode
    }

  } catch (error) {
    result.errors.push(`Exception: ${error.message}`);
  }

  return result;
}

function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run') || args.includes('-n');
  const specificFile = args.find(arg => !arg.startsWith('--') && !arg.startsWith('-'));

  console.log('🔧 SVG ViewBox Fixer');
  console.log(`Mode: ${dryRun ? 'DRY RUN (no changes will be made)' : 'LIVE (files will be modified)'}`);
  console.log('');

  if (!fs.existsSync(iconsDir)) {
    console.error(`❌ Icons directory not found: ${iconsDir}`);
    process.exit(1);
  }

  let svgFiles;
  if (specificFile) {
    const filePath = path.resolve(specificFile);
    if (!fs.existsSync(filePath)) {
      console.error(`❌ File not found: ${filePath}`);
      process.exit(1);
    }
    svgFiles = [filePath];
    console.log(`Targeting specific file: ${path.basename(filePath)}\n`);
  } else {
    svgFiles = fs.readdirSync(iconsDir)
      .filter(file => file.endsWith('.svg'))
      .map(file => path.join(iconsDir, file));
    console.log(`Found ${svgFiles.length} SVG files\n`);
  }

  const results = svgFiles.map(file => fixSvgFile(file, dryRun));
  
  const fixedFiles = results.filter(result => result.fixed);
  const errorFiles = results.filter(result => result.errors.length > 0);
  const unchangedFiles = results.filter(result => !result.fixed && result.errors.length === 0);

  console.log(`📊 Results:`);
  console.log(`  🔧 ${dryRun ? 'Would fix' : 'Fixed'}: ${fixedFiles.length}`);
  console.log(`  ❌ Errors: ${errorFiles.length}`);
  console.log(`  ✅ No changes needed: ${unchangedFiles.length}`);
  console.log('');

  if (fixedFiles.length > 0) {
    console.log(`🔧 ${dryRun ? 'Files that would be fixed' : 'Fixed files'}:\n`);
    fixedFiles.forEach(result => {
      console.log(`✅ ${result.fileName}`);
      result.changes.forEach(change => {
        console.log(`   ${change}`);
      });
      console.log('');
    });
  }

  if (errorFiles.length > 0) {
    console.log('❌ Files with errors:\n');
    errorFiles.forEach(result => {
      console.log(`❌ ${result.fileName}`);
      result.errors.forEach(error => {
        console.log(`   Error: ${error}`);
      });
      console.log('');
    });
  }

  if (dryRun && fixedFiles.length > 0) {
    console.log('\n💡 To apply fixes, run without --dry-run flag');
  }

  console.log(`\n📝 Summary: ${fixedFiles.length} files ${dryRun ? 'would be' : 'were'} fixed out of ${svgFiles.length} total`);
}

if (require.main === module) {
  main();
}

module.exports = { fixSvgFile };