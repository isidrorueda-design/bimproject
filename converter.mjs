import * as fs from 'fs';
import * as path from 'path';
import * as WEBIFC from 'web-ifc';
import * as FRAGS from '@thatopen/fragments';

const ifcFileName = process.argv[2];
const outputDir = process.argv[3];

if (!ifcFileName || !outputDir) {
    console.error("Uso: node converter.mjs <input.ifc> <outputDir>");
    process.exit(1);
}

async function convert() {
    try {
        const importer = new FRAGS.IfcImporter();
        const wasmPath = path.resolve('./node_modules/web-ifc/');
        console.log(`Configurando WASM path a: ${wasmPath}`);
        importer.wasm.path = wasmPath + '/'; 
        importer.wasm.absolute = true;
        const ifcData = fs.readFileSync(ifcFileName);
        const uint8array = new Uint8Array(ifcData);
        console.log("Iniciando conversión (API v3)...");
        const binaryData = await importer.process({
            bytes: uint8array,
            raw: false
        });

        const baseName = path.basename(ifcFileName, path.extname(ifcFileName));
        const outputFilePath = path.join(outputDir, `${baseName}.frag`);

        fs.writeFileSync(outputFilePath, binaryData);

        console.log(`Conversión exitosa: ${outputFilePath}`);

        if (importer.dispose) importer.dispose();
        process.exit(0);

    } catch (error) {
        console.error("Error durante la conversión:", error);
        process.exit(1);
    }
}

convert();
