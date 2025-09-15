#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const targetViewBox = '0 0 15 15';
const targetWidth = '15';
const targetHeight = '15';

const dir = './icons_viewbox_mismatch';

// Get all SVG files
const files = fs.readdirSync(dir).filter(file => file.endsWith('.svg'));

console.log(`Found ${files.length} SVG files to fix`);

files.forEach(file => {
  const filePath = path.join(dir, file);
  let content = fs.readFileSync(filePath, 'utf8');

  // Fix viewBox
  content = content.replace(/viewBox="[^"]*"/g, `viewBox="${targetViewBox}"`);

  // Fix width
  content = content.replace(/width="[^"]*"/g, `width="${targetWidth}"`);

  // Fix height
  content = content.replace(/height="[^"]*"/g, `height="${targetHeight}"`);

  fs.writeFileSync(filePath, content);
  console.log(`Fixed: ${file}`);
});

console.log('Done! All SVG files have been resized to 15x15 with viewBox="0 0 15 15"');