#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { parseString } = require('xml2js');

const ICONS_DIR = './icons';
const PROBLEM_DIR = './icons_viewbox_mismatch';

function parseSVG(content) {
    return new Promise((resolve, reject) => {
        parseString(content, (err, result) => {
            if (err) reject(err);
            else resolve(result);
        });
    });
}

function hasViewBoxMismatch(svgData) {
    const svg = svgData.svg.$;

    const width = parseFloat(svg.width);
    const height = parseFloat(svg.height);

    if (!svg.viewBox) {
        return false;
    }

    const viewBox = svg.viewBox.split(/\s+/).map(parseFloat);
    const [vbX, vbY, vbWidth, vbHeight] = viewBox;

    const hasNegativeOffset = vbX < 0 || vbY < 0;
    const hasPositiveOffset = vbX > 0 || vbY > 0;
    const hasSizeMismatch = Math.abs(vbWidth - width) > 0.1 || Math.abs(vbHeight - height) > 0.1;

    return hasNegativeOffset || hasPositiveOffset || hasSizeMismatch;
}

async function processSVGFiles() {
    if (!fs.existsSync(PROBLEM_DIR)) {
        fs.mkdirSync(PROBLEM_DIR, { recursive: true });
        console.log(`Created directory: ${PROBLEM_DIR}`);
    }

    const files = fs.readdirSync(ICONS_DIR).filter(file => file.endsWith('.svg'));
    console.log(`Found ${files.length} SVG files to check\n`);

    let movedCount = 0;
    let normalCount = 0;
    const problematicFiles = [];

    for (const file of files) {
        const filePath = path.join(ICONS_DIR, file);
        const content = fs.readFileSync(filePath, 'utf8');

        try {
            const svgData = await parseSVG(content);
            const svg = svgData.svg.$;

            if (hasViewBoxMismatch(svgData)) {
                const width = parseFloat(svg.width);
                const height = parseFloat(svg.height);
                const viewBox = svg.viewBox;

                console.log(`❌ ${file}`);
                console.log(`   Dimensions: ${width}×${height}`);
                console.log(`   ViewBox: ${viewBox}`);

                const destPath = path.join(PROBLEM_DIR, file);
                fs.renameSync(filePath, destPath);
                console.log(`   → Moved to ${PROBLEM_DIR}/\n`);

                problematicFiles.push({
                    file,
                    width,
                    height,
                    viewBox
                });
                movedCount++;
            } else {
                normalCount++;
            }
        } catch (error) {
            console.error(`Error processing ${file}: ${error.message}`);
        }
    }

    console.log('\n' + '='.repeat(50));
    console.log('Summary:');
    console.log(`✅ Normal files: ${normalCount}`);
    console.log(`❌ Problematic files moved: ${movedCount}`);

    if (movedCount > 0) {
        console.log(`\nAll problematic files have been moved to: ${PROBLEM_DIR}/`);

        const reportPath = path.join(PROBLEM_DIR, 'viewbox-issues-report.json');
        fs.writeFileSync(reportPath, JSON.stringify(problematicFiles, null, 2));
        console.log(`Report saved to: ${reportPath}`);
    }
}

processSVGFiles().catch(console.error);