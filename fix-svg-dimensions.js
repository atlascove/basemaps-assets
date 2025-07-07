const fs = require('fs');
const path = require('path');

// Configuration
const TARGET_HEIGHT = 15;
const TARGET_WIDTH = 15;
const TARGET_VIEWBOX = "0 0 15 15";

// Function to recursively find all SVG files
function findSvgFiles(dir) {
    const files = [];
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    
    for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            files.push(...findSvgFiles(fullPath));
        } else if (entry.isFile() && entry.name.endsWith('.svg')) {
            files.push(fullPath);
        }
    }
    return files;
}

// Function to fix SVG dimensions
function fixSvgDimensions(filePath) {
    try {
        let content = fs.readFileSync(filePath, 'utf8');
        let modified = false;
        
        // Store original content for comparison
        const originalContent = content;
        
        // Fix width attributes that are not 15
        content = content.replace(/width="(\d+)"/g, (match, width) => {
            if (parseInt(width) !== TARGET_WIDTH) {
                modified = true;
                return `width="${TARGET_WIDTH}"`;
            }
            return match;
        });
        
        // Fix height attributes that are not 15
        content = content.replace(/height="(\d+)"/g, (match, height) => {
            if (parseInt(height) !== TARGET_HEIGHT) {
                modified = true;
                return `height="${TARGET_HEIGHT}"`;
            }
            return match;
        });
        
        // Handle viewBox normalization
        content = content.replace(/viewBox="([^"]+)"/g, (match, viewBox) => {
            if (viewBox.trim() !== TARGET_VIEWBOX) {
                modified = true;
                return `viewBox="${TARGET_VIEWBOX}"`;
            }
            return match;
        });
        
        // Add explicit width/height attributes if missing
        const hasWidth = /width="/.test(content);
        const hasHeight = /height="/.test(content);
        
        if (!hasWidth || !hasHeight) {
            // Find the SVG opening tag
            content = content.replace(/<svg([^>]*)>/g, (match, attributes) => {
                let newAttributes = attributes;
                
                if (!hasWidth) {
                    newAttributes = ` width="${TARGET_WIDTH}"` + newAttributes;
                    modified = true;
                }
                if (!hasHeight) {
                    newAttributes = ` height="${TARGET_HEIGHT}"` + newAttributes;
                    modified = true;
                }
                
                return `<svg${newAttributes}>`;
            });
        }
        
        // Write back if modified
        if (modified) {
            fs.writeFileSync(filePath, content, 'utf8');
            console.log(`✅ Fixed: ${filePath}`);
            return true;
        }
        
        return false;
    } catch (error) {
        console.error(`❌ Error processing ${filePath}:`, error.message);
        return false;
    }
}

// Function to analyze SVG dimensions
function analyzeSvgDimensions(dir) {
    const svgFiles = findSvgFiles(dir);
    const stats = {
        total: svgFiles.length,
        widthStats: {},
        heightStats: {},
        viewBoxStats: {},
        fixed: 0
    };
    
    console.log(`🔍 Found ${svgFiles.length} SVG files`);
    console.log('📊 Analyzing dimensions...\n');
    
    for (const filePath of svgFiles) {
        try {
            const content = fs.readFileSync(filePath, 'utf8');
            
            // Extract width
            const widthMatch = content.match(/width="(\d+)"/);
            if (widthMatch) {
                const width = widthMatch[1];
                stats.widthStats[width] = (stats.widthStats[width] || 0) + 1;
            }
            
            // Extract height
            const heightMatch = content.match(/height="(\d+)"/);
            if (heightMatch) {
                const height = heightMatch[1];
                stats.heightStats[height] = (stats.heightStats[height] || 0) + 1;
            }
            
            // Extract viewBox
            const viewBoxMatch = content.match(/viewBox="([^"]+)"/);
            if (viewBoxMatch) {
                const viewBox = viewBoxMatch[1].trim();
                stats.viewBoxStats[viewBox] = (stats.viewBoxStats[viewBox] || 0) + 1;
            }
            
            // Fix if needed
            if (fixSvgDimensions(filePath)) {
                stats.fixed++;
            }
            
        } catch (error) {
            console.error(`❌ Error reading ${filePath}:`, error.message);
        }
    }
    
    return stats;
}

// Main execution
function main() {
    const iconsDir = './icons';
    
    console.log('🚀 Starting SVG dimension alignment...\n');
    
    // Check if icons directory exists
    if (!fs.existsSync(iconsDir)) {
        console.error('❌ Icons directory not found! Please run this script from the project root.');
        process.exit(1);
    }
    
    // Analyze and fix
    const stats = analyzeSvgDimensions(iconsDir);
    
    // Print results
    console.log('\n📈 RESULTS:');
    console.log(`📁 Total files processed: ${stats.total}`);
    console.log(`🔧 Files fixed: ${stats.fixed}`);
    
    console.log('\n📏 Width distribution:');
    Object.entries(stats.widthStats)
        .sort((a, b) => parseInt(b[1]) - parseInt(a[1]))
        .forEach(([width, count]) => {
            const emoji = width === TARGET_WIDTH.toString() ? '✅' : '⚠️';
            console.log(`  ${emoji} width="${width}": ${count} files`);
        });
    
    console.log('\n📐 Height distribution:');
    Object.entries(stats.heightStats)
        .sort((a, b) => parseInt(b[1]) - parseInt(a[1]))
        .forEach(([height, count]) => {
            const emoji = height === TARGET_HEIGHT.toString() ? '✅' : '⚠️';
            console.log(`  ${emoji} height="${height}": ${count} files`);
        });
    
    console.log('\n🎯 ViewBox distribution:');
    Object.entries(stats.viewBoxStats)
        .sort((a, b) => parseInt(b[1]) - parseInt(a[1]))
        .forEach(([viewBox, count]) => {
            const emoji = viewBox === TARGET_VIEWBOX ? '✅' : '⚠️';
            console.log(`  ${emoji} viewBox="${viewBox}": ${count} files`);
        });
    
    if (stats.fixed > 0) {
        console.log(`\n🎉 Successfully aligned ${stats.fixed} SVG files to ${TARGET_WIDTH}x${TARGET_HEIGHT} dimensions with viewBox="${TARGET_VIEWBOX}"!`);
    } else {
        console.log('\n✨ All SVG files already have correct dimensions!');
    }
}

// Run the script
if (require.main === module) {
    main();
}

module.exports = {
    findSvgFiles,
    fixSvgDimensions,
    analyzeSvgDimensions
}; 