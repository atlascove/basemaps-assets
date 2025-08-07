#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { DOMParser } = require('xmldom');

const iconsDir = path.join(__dirname, 'icons');

function testSvgFile(filePath) {
  const fileName = path.basename(filePath);
  const results = {
    fileName,
    filePath,
    isValid: false,
    isEmpty: false,
    errors: []
  };

  try {
    const content = fs.readFileSync(filePath, 'utf8');
    
    if (!content || content.trim().length === 0) {
      results.isEmpty = true;
      results.errors.push('File is empty');
      return results;
    }

    if (content.length < 50) {
      results.errors.push('File content is suspiciously short');
    }

    if (!content.includes('<svg')) {
      results.errors.push('Missing <svg> tag');
      return results;
    }

    const parser = new DOMParser({
      errorHandler: {
        warning: (msg) => results.errors.push(`Warning: ${msg}`),
        error: (msg) => results.errors.push(`Error: ${msg}`),
        fatalError: (msg) => results.errors.push(`Fatal Error: ${msg}`)
      }
    });

    const doc = parser.parseFromString(content, 'text/xml');
    
    if (!doc) {
      results.errors.push('Failed to parse XML');
      return results;
    }

    const svgElement = doc.getElementsByTagName('svg')[0];
    if (!svgElement) {
      results.errors.push('No SVG element found');
      return results;
    }

    const hasPath = svgElement.getElementsByTagName('path').length > 0;
    const hasCircle = svgElement.getElementsByTagName('circle').length > 0;
    const hasRect = svgElement.getElementsByTagName('rect').length > 0;
    const hasPolygon = svgElement.getElementsByTagName('polygon').length > 0;
    const hasLine = svgElement.getElementsByTagName('line').length > 0;
    const hasG = svgElement.getElementsByTagName('g').length > 0;

    if (!hasPath && !hasCircle && !hasRect && !hasPolygon && !hasLine && !hasG) {
      results.errors.push('SVG appears to have no drawable content');
    }

    const viewBox = svgElement.getAttribute('viewBox');
    const width = svgElement.getAttribute('width');
    const height = svgElement.getAttribute('height');

    if (!viewBox && (!width || !height)) {
      results.errors.push('SVG has no viewBox or dimensions specified');
    }

    results.isValid = results.errors.length === 0;
    
  } catch (error) {
    results.errors.push(`Exception: ${error.message}`);
  }

  return results;
}

function main() {
  console.log('🔍 Testing SVG files for faults and emptiness...\n');
  
  if (!fs.existsSync(iconsDir)) {
    console.error(`❌ Icons directory not found: ${iconsDir}`);
    process.exit(1);
  }

  const svgFiles = fs.readdirSync(iconsDir)
    .filter(file => file.endsWith('.svg'))
    .map(file => path.join(iconsDir, file));

  console.log(`Found ${svgFiles.length} SVG files\n`);

  const results = svgFiles.map(testSvgFile);
  
  const faultyFiles = results.filter(result => !result.isValid || result.isEmpty);
  const validFiles = results.filter(result => result.isValid && !result.isEmpty);

  console.log(`📊 Results:`);
  console.log(`  ✅ Valid files: ${validFiles.length}`);
  console.log(`  ❌ Faulty/Empty files: ${faultyFiles.length}`);
  console.log('');

  if (faultyFiles.length > 0) {
    console.log('🚨 Faulty/Empty SVG Files:\n');
    
    faultyFiles.forEach(result => {
      console.log(`❌ ${result.fileName}`);
      console.log(`   Path: ${result.filePath}`);
      if (result.isEmpty) {
        console.log(`   🔍 Status: EMPTY FILE`);
      }
      result.errors.forEach(error => {
        console.log(`   🔍 Issue: ${error}`);
      });
      console.log('');
    });

    console.log(`\n📝 Summary: ${faultyFiles.length} files need attention out of ${svgFiles.length} total SVG files`);
    process.exit(1);
  } else {
    console.log('🎉 All SVG files are valid!');
    process.exit(0);
  }
}

if (require.main === module) {
  main();
}

module.exports = { testSvgFile };