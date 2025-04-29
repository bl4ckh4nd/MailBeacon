import React, { useState } from 'react';
import { Box, Typography, Button, Alert, CircularProgress } from '@mui/material';
import FileUpload from '../components/FileUpload';
import ResultsTable from '../components/ResultsTable';
import LoadingSpinner from '../components/LoadingSpinner';
import { useFindBatchEmails } from '../hooks/useApi';
import { ProcessingResult, BatchContactRequest, SingleContactRequest } from '../types';
// Need a CSV parsing library
import Papa, { ParseResult } from 'papaparse';

// Define expected structure of a row from CSV
interface CsvRowData {
    first_name?: string;
    last_name?: string;
    full_name?: string;
    domain?: string;
    company_domain?: string; // Allow alias
    company?: string;
    // Allow other potential columns, though we won't use them directly
    [key: string]: string | undefined;
}

const BatchFinderPage: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [parsedContacts, setParsedContacts] = useState<SingleContactRequest[]>([]);
  const [isParsingOrLoading, setIsParsingOrLoading] = useState<boolean>(false);
  const [fileError, setFileError] = useState<string | null>(null);

  const {
      data: results,
      isLoading: isApiLoading,
      error: apiError,
      execute: processBatch
  } = useFindBatchEmails();

  const isLoading = isParsingOrLoading || isApiLoading;

  const handleFileAccepted = (acceptedFile: File | null) => {
    if (!acceptedFile) {
        setFile(null);
        setParsedContacts([]);
        setFileError(null);
        setIsParsingOrLoading(false);
        return;
    }

    setFile(acceptedFile);
    setParsedContacts([]);
    setFileError(null);
    setIsParsingOrLoading(true);

    if (acceptedFile.type === 'text/csv' || acceptedFile.name.endsWith('.csv')) {
        Papa.parse<CsvRowData>(acceptedFile, {
            header: true,
            skipEmptyLines: true,
            complete: (parseResult: ParseResult<CsvRowData>) => {
                console.log('Parse Complete:', parseResult);
                if (parseResult.errors.length > 0) {
                    setFileError(`Error parsing CSV (Code: ${parseResult.errors[0].code}): ${parseResult.errors[0].message} on row ${parseResult.errors[0].row}`);
                    setIsParsingOrLoading(false);
                    return;
                }
                const contacts: SingleContactRequest[] = [];
                let headerError = false;
                parseResult.data.forEach((row: CsvRowData, index: number) => {
                    const hasFirstLast = row.first_name && row.last_name;
                    const hasFullName = row.full_name;
                    const hasDomain = row.domain || row.company_domain;

                    if (!( (hasFirstLast || hasFullName) && hasDomain )) {
                        // Check if it's just an empty row at the end before erroring
                        if (Object.values(row).every(val => !val)) {
                            console.log(`Skipping empty row ${index + 1}`);
                            return; // Skip likely empty row
                        }
                        setFileError(`Missing required columns in row ${index + 1}. Need (first_name AND last_name) OR full_name, AND (domain OR company_domain).`);
                        headerError = true;
                        return; // Stop processing this row
                    }

                    if (!headerError) {
                        contacts.push({
                            first_name: row.first_name?.trim() || null,
                            last_name: row.last_name?.trim() || null,
                            full_name: row.full_name?.trim() || null,
                            domain: row.domain?.trim() || row.company_domain?.trim() || null,
                            company: row.company?.trim() || null,
                        });
                    }
                });

                if (headerError) {
                   setIsParsingOrLoading(false);
                   setParsedContacts([]);
                   setFile(null);
                   return;
                }

                if (contacts.length === 0 && !headerError) {
                     setFileError('CSV file appears to be empty or no valid contact rows found.');
                } else {
                    setParsedContacts(contacts);
                    setFileError(null);
                    console.log('Parsed Contacts:', contacts);
                }
                setIsParsingOrLoading(false);
            },
            error: (err: Error) => {
                console.error('Papaparse error:', err);
                setFileError(`Failed to parse file: ${err.message}`);
                setIsParsingOrLoading(false);
            }
        });
    } else if (acceptedFile.name.endsWith('.xlsx')) {
        setFileError('XLSX parsing is not yet implemented. Please use CSV.');
        setFile(null);
        setIsParsingOrLoading(false);
    } else {
        setFileError('Unsupported file type. Please upload a CSV or XLSX file.');
        setFile(null);
        setIsParsingOrLoading(false);
    }
  };

  const handleProcessBatch = async () => {
    if (parsedContacts.length === 0) {
        setFileError('No valid contacts found in the file to process.');
        return;
    }
    setFileError(null);

    const batchRequest: BatchContactRequest = { contacts: parsedContacts };

    try {
        await processBatch(batchRequest);
    } catch (err) {
        console.error('Batch Find Error caught in component:', err);
    }
  };

  return (
    <div className="w-full">
      <h2 className="text-2xl font-semibold text-center mb-6 text-gray-800">
        Batch Email Finder
      </h2>

      <FileUpload onFileAccepted={handleFileAccepted} />

      {fileError && (
          <Alert 
              severity="warning" 
              className="mt-4 p-4 rounded-md border border-yellow-300 bg-yellow-50 text-yellow-800 text-sm"
           >
              {fileError}
          </Alert>
      )}

      {parsedContacts.length > 0 && !fileError && (
           <div className="bg-white p-4 shadow-md rounded-lg mt-4 flex flex-col sm:flex-row justify-between items-center space-y-2 sm:space-y-0 sm:space-x-4">
               <p className="text-sm text-gray-700 text-center sm:text-left">
                   Found <span className="font-semibold">{parsedContacts.length}</span> contacts ready to process.
                </p>
               <Button
                  variant="contained"
                  onClick={handleProcessBatch}
                  disabled={isLoading || parsedContacts.length === 0}
                  className="bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2 px-5 rounded-md transition duration-150 ease-in-out disabled:opacity-60 disabled:cursor-not-allowed shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-sky-500 w-full sm:w-auto"
                >
                   {isApiLoading ? (
                       <span className="flex items-center justify-center">
                           <CircularProgress size={20} color="inherit" className="mr-2" />
                           Processing...
                       </span>
                   ) : (
                      'Process Batch'
                   )}
               </Button>
            </div>
      )}

      <div className="mt-8">
          {isLoading && <LoadingSpinner />} 

          {apiError && !isParsingOrLoading && (
              <Alert 
                  severity="error" 
                  className="mt-4 p-4 rounded-md border border-red-300 bg-red-50 text-red-700 text-sm"
              >
                  Error: {apiError.message}
              </Alert>
          )}

          {results && results.length > 0 && !isLoading && !fileError && (
              <ResultsTable results={results} isLoading={isApiLoading} />
          )}
          {!isLoading && !fileError && !apiError && results && results.length === 0 && parsedContacts.length > 0 && file && (
              <p className="text-center mt-6 text-gray-600 text-sm">
                  Processing finished, but no results were returned from the API.
              </p>
          )}
      </div>
    </div>
  );
};

export default BatchFinderPage; 