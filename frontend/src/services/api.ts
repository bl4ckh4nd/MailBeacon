import axios from 'axios';
import { config } from '../config';
import {
    SingleContactRequest,
    BatchContactRequest,
    ProcessingResult
} from '../types';

// Create an Axios instance with default settings
const apiClient = axios.create({
  // baseURL: config.api.baseUrl, // Base URL is included in endpoint URLs in config
  headers: {
    'Content-Type': 'application/json',
    // Add other headers like Authorization if needed later
  },
  // timeout: config.api.defaultTimeout || 15000, // Optional: Add a timeout
});

// --- API Functions ---

/**
 * Fetches the email for a single contact.
 * @param contact The contact information.
 * @returns A promise that resolves with the processing result.
 * @throws Throws an error if the API request fails.
 */
export const findSingleEmail = async (
    contact: SingleContactRequest
): Promise<ProcessingResult> => {
  try {
    console.log('Sending request to:', config.api.endpoints.single, contact);
    const response = await apiClient.post<ProcessingResult>(
        config.api.endpoints.single,
        contact
    );
    console.log('Received response (single):', response.data);
    return response.data;
  } catch (error) {
    console.error("API Error (findSingleEmail):", error);
    // Enhance error reporting
    if (axios.isAxiosError(error)) {
        if (error.response) {
            // The request was made and the server responded with a status code
            // that falls out of the range of 2xx
            console.error('Error data:', error.response.data);
            console.error('Error status:', error.response.status);
            // Try to extract Pydantic validation error details
            const detail = error.response.data?.detail;
            if (detail) {
                if (Array.isArray(detail)) {
                  // Handle complex Pydantic errors (e.g., multiple field errors)
                  const messages = detail.map((d: any) => `${d.loc?.join('.') || 'field'}: ${d.msg}`).join('; ');
                  throw new Error(`API Validation Error: ${messages}`);
                } else if (typeof detail === 'string'){
                   throw new Error(`API Error: ${detail}`);
                }
            }
            throw new Error(`API Error: Status ${error.response.status} - ${error.response.statusText}`);
        } else if (error.request) {
            // The request was made but no response was received
            console.error('Error request:', error.request);
            throw new Error('Network Error: No response received from server.');
        } else {
            // Something happened in setting up the request that triggered an Error
            console.error('Error message:', error.message);
            throw new Error(`Request Setup Error: ${error.message}`);
        }
    } else {
        // Non-Axios error
        throw new Error('An unexpected error occurred.');
    }
 }
};

/**
 * Processes a batch of contacts to find their emails.
 * @param batchRequest The batch request containing multiple contacts.
 * @returns A promise that resolves with an array of processing results.
 * @throws Throws an error if the API request fails.
 */
export const findBatchEmails = async (
    batchRequest: BatchContactRequest
): Promise<ProcessingResult[]> => {
  try {
    console.log('Sending request to:', config.api.endpoints.batch, batchRequest);
    const response = await apiClient.post<ProcessingResult[]>(
        config.api.endpoints.batch,
        batchRequest
    );
    console.log('Received response (batch):', response.data);
    return response.data;
  } catch (error) {
      console.error("API Error (findBatchEmails):", error);
      // Reusing the enhanced error handling from findSingleEmail
      if (axios.isAxiosError(error)) {
          if (error.response) {
            const detail = error.response.data?.detail;
             if (detail) {
                if (Array.isArray(detail)) {
                  const messages = detail.map((d: any) => `${d.loc?.join('.') || 'field'}: ${d.msg}`).join('; ');
                  throw new Error(`API Validation Error: ${messages}`);
                } else if (typeof detail === 'string'){
                   throw new Error(`API Error: ${detail}`);
                }
            }
            throw new Error(`API Error: Status ${error.response.status} - ${error.response.statusText}`);
          } else if (error.request) {
              throw new Error('Network Error: No response received from server.');
          } else {
              throw new Error(`Request Setup Error: ${error.message}`);
          }
      } else {
          throw new Error('An unexpected error occurred.');
      }
  }
};

/**
 * Checks the health of the backend API.
 * @returns A promise that resolves with the health status.
 * @throws Throws an error if the API request fails.
 */
export const checkHealth = async (): Promise<{ status: string }> => {
    try {
        console.log('Sending request to:', config.api.endpoints.health);
        const response = await apiClient.get<{ status: string }>(config.api.endpoints.health);
        console.log('Received response (health):', response.data);
        return response.data;
    } catch (error) {
        console.error("API Error (checkHealth):", error);
        // Reusing the enhanced error handling
        if (axios.isAxiosError(error)) {
             if (error.response) {
                throw new Error(`API Error: Status ${error.response.status} - ${error.response.statusText}`);
             } else if (error.request) {
                 throw new Error('Network Error: No response received from server.');
             } else {
                 throw new Error(`Request Setup Error: ${error.message}`);
             }
         } else {
             throw new Error('An unexpected error occurred checking API health.');
         }
    }
} 