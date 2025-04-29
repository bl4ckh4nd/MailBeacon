import React from 'react';
// Remove MUI imports 
// import { Box, Typography, Paper } from '@mui/material';
import { ProcessingResult } from '../types';
import LoadingSpinner from './LoadingSpinner'; // Keep spinner

interface ResultsTableProps {
  results: ProcessingResult[];
  isLoading: boolean;
}

const ResultsTable: React.FC<ResultsTableProps> = ({ results, isLoading }) => {
  if (isLoading) {
    return <LoadingSpinner />; // Use centered spinner
  }

  if (!results || results.length === 0) {
    // Return null or a subtle message if no results, handled by parent page
    return null; 
  }

  // Basic Tailwind table structure (Needs improvement for real data)
  return (
    <div className="bg-white shadow-md rounded-lg mt-6 overflow-x-auto">
      <h2 className="text-lg font-semibold text-gray-700 p-4 border-b border-gray-200">
        Batch Results ({results.length})
      </h2>
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {/* Define basic columns - Adjust based on important fields */} 
            <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
            <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Domain</th>
            <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Found Email</th>
            <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
            {/* Add more columns as needed (e.g., Alternatives, Verification) */} 
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {results.map((result, index) => (
            <tr key={index} className="hover:bg-gray-50">
              <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-800">{result.contact_input.full_name || `${result.contact_input.first_name || ''} ${result.contact_input.last_name || ''}`.trim()}</td>
              <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-800">{result.contact_input.domain}</td>
              <td className="px-4 py-2 whitespace-nowrap text-sm">
                  {/* Add status indicator (e.g., badge) based on result */} 
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                      ${result.email ? 'bg-green-100 text-green-800' : result.email_finding_skipped ? 'bg-yellow-100 text-yellow-800' : result.email_finding_error ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}
                  `}>
                     {result.email ? 'Success' : result.email_finding_skipped ? 'Skipped' : result.email_finding_error ? 'Error' : 'Not Found'}
                  </span>
              </td>
              <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-800">{result.email || '-'}</td>
              <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">{result.email_confidence !== null ? `${result.email_confidence}/10` : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {/* Add Pagination and Export Button later */} 
    </div>
  );
};

export default ResultsTable; 