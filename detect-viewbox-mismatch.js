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

function checkViewBoxMismatch(filePath) {
  const fileName = path.basename(filePath);
  const result = {
    fileName,
    filePath,
    hasMismatch: false,
    issues: [],
    viewBox: null,
    pathBounds: null
  };

  try {
    const content = fs.readFileSync(filePath, 'utf8');
    
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
      result.issues.push('No SVG element found');
      return result;
    }

    // Get viewBox
    const viewBoxAttr = svgElement.getAttribute('viewBox');
    if (!viewBoxAttr) {
      result.issues.push('No viewBox attribute found');
      return result;
    }

    const viewBoxParts = viewBoxAttr.split(/\s+/).map(parseFloat);
    if (viewBoxParts.length !== 4) {
      result.issues.push('Invalid viewBox format');
      return result;
    }

    const [vbMinX, vbMinY, vbWidth, vbHeight] = viewBoxParts;
    const vbMaxX = vbMinX + vbWidth;
    const vbMaxY = vbMinY + vbHeight;
    
    result.viewBox = { minX: vbMinX, minY: vbMinY, maxX: vbMaxX, maxY: vbMaxY, width: vbWidth, height: vbHeight };

    // Analyze all path elements
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

    // Also check other shape elements
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
        }

        if (width > 0 || height > 0) {
          globalMinX = Math.min(globalMinX, x);
          globalMinY = Math.min(globalMinY, y);
          globalMaxX = Math.max(globalMaxX, x + width);
          globalMaxY = Math.max(globalMaxY, y + height);
          hasValidPaths = true;
        }
      }
    });

    if (!hasValidPaths) {
      result.issues.push('No drawable content with coordinates found');
      return result;
    }

    result.pathBounds = { minX: globalMinX, minY: globalMinY, maxX: globalMaxX, maxY: globalMaxY };

    // Check for mismatch with tolerance
    const tolerance = 5;
    const pathOutsideViewBox = 
      globalMaxX > vbMaxX + tolerance ||
      globalMaxY > vbMaxY + tolerance ||
      globalMinX < vbMinX - tolerance ||
      globalMinY < vbMinY - tolerance;

    if (pathOutsideViewBox) {
      result.hasMismatch = true;
      result.issues.push(`Path coordinates (${globalMinX.toFixed(1)}, ${globalMinY.toFixed(1)}) to (${globalMaxX.toFixed(1)}, ${globalMaxY.toFixed(1)}) extend outside viewBox (${vbMinX}, ${vbMinY}) to (${vbMaxX}, ${vbMaxY})`);
    }

    // Check if viewBox is much larger than needed
    const pathWidth = globalMaxX - globalMinX;
    const pathHeight = globalMaxY - globalMinY;
    const viewBoxWaste = (vbWidth * vbHeight) / (pathWidth * pathHeight);
    
    if (viewBoxWaste > 10 && (vbWidth > pathWidth * 2 || vbHeight > pathHeight * 2)) {
      result.hasMismatch = true;
      result.issues.push(`ViewBox is much larger than needed - viewBox: ${vbWidth}x${vbHeight}, content: ${pathWidth.toFixed(1)}x${pathHeight.toFixed(1)}`);
    }

  } catch (error) {
    result.issues.push(`Error parsing SVG: ${error.message}`);
  }

  return result;
}

function main() {
  console.log('🔍 Checking SVG files for viewBox mismatch issues...\n');
  
  if (!fs.existsSync(iconsDir)) {
    console.error(`❌ Icons directory not found: ${iconsDir}`);
    process.exit(1);
  }

  const svgFiles = fs.readdirSync(iconsDir)
    .filter(file => file.endsWith('.svg'))
    .map(file => path.join(iconsDir, file));

  console.log(`Found ${svgFiles.length} SVG files\n`);

  const results = svgFiles.map(checkViewBoxMismatch);
  
  const problematicFiles = results.filter(result => result.hasMismatch || result.issues.length > 0);
  const validFiles = results.filter(result => !result.hasMismatch && result.issues.length === 0);

  console.log(`📊 Results:`);
  console.log(`  ✅ Valid files: ${validFiles.length}`);
  console.log(`  ❌ Problematic files: ${problematicFiles.length}`);
  console.log('');

  if (problematicFiles.length > 0) {
    console.log('🚨 Files with ViewBox Issues:\n');
    
    problematicFiles.forEach(result => {
      console.log(`❌ ${result.fileName}`);
      if (result.viewBox) {
        console.log(`   ViewBox: ${result.viewBox.minX}, ${result.viewBox.minY}, ${result.viewBox.width}, ${result.viewBox.height}`);
      }
      if (result.pathBounds) {
        console.log(`   Content bounds: (${result.pathBounds.minX.toFixed(1)}, ${result.pathBounds.minY.toFixed(1)}) to (${result.pathBounds.maxX.toFixed(1)}, ${result.pathBounds.maxY.toFixed(1)})`);
      }
      result.issues.forEach(issue => {
        console.log(`   🔍 Issue: ${issue}`);
      });
      console.log('');
    });

    console.log(`\n📝 Summary: ${problematicFiles.length} files have viewBox issues out of ${svgFiles.length} total SVG files`);
  } else {
    console.log('🎉 All SVG files have proper viewBox settings!');
  }
}

if (require.main === module) {
  main();
}

module.exports = { checkViewBoxMismatch };