<?php
// iloveimg_processor.php - Script PHP para ser llamado por Python
// Este script procesa una imagen con iLoveIMG y devuelve la URL de descarga.

require_once __DIR__ . '/vendor/autoload.php';

use Iloveimg\Iloveimg;

// --- Funciones auxiliares para salida ---
function outputError($message) {
    file_put_contents('php://stderr', "ERROR: " . $message . "\n");
    exit(1);
}

function outputSuccess($url) {
    echo $url . "\n";
    exit(0);
}

// --- Validación de argumentos ---
$args = $_SERVER['argv'];
if (count($args) < 6) {
    outputError("Uso: php iloveimg_processor.php <tmp_file_path> <original_filename> <iloveimg_public_key> <iloveimg_secret_key> [output_filename]");
}

$tmpFilePath         = $args[1];
$originalFilename    = $args[2];
$iloveimgPublicKey   = $args[3];
$iloveimgSecretKey   = $args[4];
$outputFilename      = $args[5] ?? null; // Opcional

if (!file_exists($tmpFilePath)) {
    outputError("El archivo temporal no existe: " . $tmpFilePath);
}

// --- Procesamiento con iLoveIMG ---
try {
    $iloveimg = new Iloveimg($iloveimgPublicKey, $iloveimgSecretKey);
    
    // Tarea para quitar el fondo
    $removeBgTask = $iloveimg->newTask('removebackground');
    $file = $removeBgTask->addFile($tmpFilePath);
    $file->setFilename($originalFilename);
    $removeBgTask->execute();

    // Encadenar tarea de compresión
    $compressTask = $removeBgTask->next('compress');
    $compressTask->setCompressionLevel('recommended');

    // Si se especificó un nombre de archivo de salida
    if ($outputFilename) {
        $compressTask->setoutputFileName($outputFilename);
    }
    
    $compressTask->execute();

    // Devolver la URL de descarga del archivo procesado
    outputSuccess($compressTask->getDownloadUrl());

} catch (Exception $e) {
    outputError("Fallo en el procesamiento de iLoveIMG: " . $e->getMessage());
}
