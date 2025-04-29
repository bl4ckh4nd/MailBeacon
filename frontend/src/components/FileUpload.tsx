import React, { useState, useCallback } from 'react';
import { useDropzone, FileRejection } from 'react-dropzone';
import { Typography, Button } from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import DescriptionIcon from '@mui/icons-material/Description';

interface FileUploadProps {
  onFileAccepted: (file: File | null) => void; // Allow null for clearing
  acceptedFileTypes?: { [key: string]: string[] };
  maxFileSize?: number; // in bytes
}

// Placeholder for File Upload component
const FileUpload: React.FC<FileUploadProps> = ({ 
    onFileAccepted, 
    acceptedFileTypes = { 'text/csv': ['.csv'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] }, // Default to CSV and XLSX
    maxFileSize = 10 * 1024 * 1024 // Default 10MB
}) => {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[], fileRejections: FileRejection[]) => {
    setError(null);
    setUploadedFile(null);
    onFileAccepted(null); // Notify parent that selection is reset

    if (fileRejections.length > 0) {
        const firstRejection = fileRejections[0];
        const errorMessages = firstRejection.errors.map((e) => e.message).join(', ');
        setError(`File rejected: ${errorMessages}`);
        return;
    }

    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setUploadedFile(file);
      onFileAccepted(file); // Notify parent of accepted file
      console.log('File accepted:', file.name);
    } else {
        // This case might not be needed if dropzone handles rejections properly
    }
  }, [onFileAccepted]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedFileTypes,
    maxSize: maxFileSize,
    multiple: false // Allow only single file upload
  });

  const clearSelection = () => {
      setUploadedFile(null);
      setError(null);
      onFileAccepted(null); // Notify parent that selection is cleared
  };

  return (
    <div className="bg-white p-6 shadow-lg rounded-lg mt-4">
        <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors duration-200 ease-in-out mb-4 
                ${isDragActive ? 'border-sky-500 bg-sky-50' : 'border-gray-300 bg-gray-50 hover:border-gray-400'}
                ${error ? 'border-red-500 bg-red-50' : ''}`
            }
        >
            <input {...getInputProps()} />
            <UploadFileIcon className="mx-auto h-12 w-12 text-gray-400 mb-2" />
            {isDragActive ? (
                <p className="mt-2 text-sm font-medium text-sky-600">Drop the file here ...</p>
            ) : (
                <p className="mt-2 text-sm text-gray-600">Drag & drop a CSV or XLSX file here, or click to select</p>
            )}
            <p className="mt-1 text-xs text-gray-500">
                (Max size: {maxFileSize / 1024 / 1024}MB)
            </p>
        </div>

        <div className="min-h-[44px] flex items-center">
            {uploadedFile && !error && (
                <div className="flex items-center justify-between text-sm text-gray-700 bg-gray-100 p-2.5 rounded-md w-full">
                   <div className="flex items-center min-w-0">
                        <DescriptionIcon className="h-5 w-5 mr-2 text-gray-500 flex-shrink-0" />
                        <span className="font-medium truncate block" title={uploadedFile.name}>{uploadedFile.name}</span>
                        <span className="ml-2 text-gray-500 flex-shrink-0">({(uploadedFile.size / 1024).toFixed(1)} KB)</span>
                    </div>
                    <Button 
                        size="small" 
                        onClick={clearSelection} 
                        className="text-xs text-red-600 hover:bg-red-50 ml-2 p-1 rounded leading-none flex-shrink-0"
                        aria-label="Clear selection"
                        sx={{ minWidth: 'auto' }}
                    >
                        Clear
                    </Button>
                </div>
            )}

            {error && (
                <p className="text-sm text-red-600 p-2 w-full">
                    {error}
                </p>
            )}
         </div>

    </div>
  );
};

export default FileUpload; 