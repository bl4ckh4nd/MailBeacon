import React from 'react';
import { Button, CircularProgress, Alert, Typography } from '@mui/material';
import { useForm, SubmitHandler, FieldError } from 'react-hook-form';
import { useFindSingleEmail } from '../hooks/useApi';
import { ProcessingResult, SingleContactRequest } from '../types';
import ResultDisplay from '../components/ResultDisplay';
import LoadingSpinner from '../components/LoadingSpinner';

// Define the form data structure explicitly
interface SingleFinderFormData {
    firstName?: string;
    lastName?: string;
    fullName?: string;
    domain: string;
}

// Helper to generate Tailwind classes for form inputs
const getInputClasses = (error?: FieldError): string => {
    const baseClasses = "mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-sky-500 focus:border-sky-500 sm:text-sm";
    const errorClasses = "border-red-500 ring-red-500 focus:border-red-500 focus:ring-red-500";
    const disabledClasses = "disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed";
    return `${baseClasses} ${error ? errorClasses : ''} ${disabledClasses}`;
};

// Helper for input labels
const labelClasses = "block text-sm font-medium text-gray-700";

const SingleFinderPage: React.FC = () => {
  const { register, handleSubmit, formState: { errors }, watch, setValue } = useForm<SingleFinderFormData>({
    mode: 'onSubmit',
    defaultValues: {
        firstName: '',
        lastName: '',
        fullName: '',
        domain: ''
    }
  });
  const { data: result, isLoading, error: apiError, execute: findEmail } = useFindSingleEmail();
  const [validationError, setValidationError] = React.useState<string | null>(null);

  const firstName = watch('firstName');
  const lastName = watch('lastName');
  const fullName = watch('fullName');

  React.useEffect(() => {
      if (firstName || lastName) {
          setValue('fullName', '', { shouldValidate: false });
      }
  }, [firstName, lastName, setValue]);

  React.useEffect(() => {
      if (fullName) {
          setValue('firstName', '', { shouldValidate: false });
          setValue('lastName', '', { shouldValidate: false });
      }
  }, [fullName, setValue]);

  const onSubmit: SubmitHandler<SingleFinderFormData> = async (data) => {
    setValidationError(null);

    if (!data.domain || data.domain.trim() === '') {
        setValidationError("Domain or Website URL is required.");
        return;
    }
    if (!data.fullName?.trim() && (!data.firstName?.trim() || !data.lastName?.trim())) {
         setValidationError("Please provide Full Name OR both First and Last Name.");
         return;
    }

    const requestData: SingleContactRequest = {
        first_name: data.firstName?.trim() || null,
        last_name: data.lastName?.trim() || null,
        full_name: data.fullName?.trim() || null,
        domain: data.domain.trim(),
        company: null
    };

    try {
      await findEmail(requestData);
    } catch (error) {
        console.error('Single Find Error caught in component:', error);
    }
  };

  return (
    <div className="w-full">
       <h2 className="text-2xl font-semibold text-center mb-6 text-gray-800">
         Find Single Email
       </h2>
       <div className="bg-white p-6 md:p-8 shadow-lg rounded-lg">
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
              <div>
                  <label htmlFor="firstName" className={labelClasses}>First Name</label>
                  <input 
                      type="text" 
                      id="firstName" 
                      className={getInputClasses()} 
                      disabled={!!fullName?.trim()}
                      {...register("firstName")}
                   />
              </div>
              <div>
                 <label htmlFor="lastName" className={labelClasses}>Last Name</label>
                 <input 
                      type="text" 
                      id="lastName" 
                      className={getInputClasses()} 
                      disabled={!!fullName?.trim()}
                      {...register("lastName")}
                 />
              </div>
          </div>
           <div className="text-center my-4 relative">
                <hr className="absolute left-0 right-0 top-1/2 border-t border-gray-200" />
                <span className="relative bg-white px-2 text-sm text-gray-500">OR</span>
           </div>
           <div className="mb-4">
              <label htmlFor="fullName" className={labelClasses}>Full Name</label>
              <input 
                  type="text" 
                  id="fullName" 
                  className={getInputClasses()} 
                  disabled={!!firstName?.trim() || !!lastName?.trim()}
                  {...register("fullName")}
               />
           </div>
            <div className="mb-6">
              <label htmlFor="domain" className={labelClasses}>
                  Domain or Website URL <span className="text-red-500">*</span>
              </label>
              <input 
                  type="text" 
                  id="domain" 
                  placeholder="example.com or https://www.example.com"
                  className={getInputClasses(errors.domain)}
                  {...register("domain", {
                       required: "Domain is required",
                       pattern: {
                          value: /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}|(?:https?:\/\/)?(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$/i,
                          message: "Please enter a valid domain or URL"
                       }
                  })}
               />
               {errors.domain ? (
                  <p className="mt-1 text-xs text-red-600">{errors.domain.message}</p> 
               ) : (
                  <p className="mt-1 text-xs text-gray-500">e.g., company.com or www.company.com</p> 
               )}
            </div>
            <div className="text-center mt-6">
              <Button
                type="submit"
                variant="contained"
                disabled={isLoading}
                className="bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2.5 px-6 rounded-md min-w-[150px] transition duration-150 ease-in-out disabled:opacity-60 disabled:cursor-not-allowed shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-sky-500"
              >
                {isLoading ? (
                    <span className="flex items-center justify-center">
                         <CircularProgress size={20} color="inherit" className="mr-2" />
                         Searching...
                    </span>
                 ) : (
                    'Find Email'
                )}
              </Button>
            </div>
          </form>
        </div>

      <div className="mt-8">
          {isLoading && <LoadingSpinner />}

          {validationError && (
              <Alert severity="warning" className="mt-4 p-4 rounded-md border border-yellow-300 bg-yellow-50 text-yellow-800">
                  {validationError}
              </Alert>
          )}

          {apiError && !validationError && (
              <Alert severity="error" className="mt-4 p-4 rounded-md border border-red-300 bg-red-50 text-red-700">
                   Error: {apiError.message}
              </Alert>
          )}

          {!isLoading && !validationError && result && (
            <ResultDisplay result={result} />
          )}
      </div>
    </div>
  );
};

export default SingleFinderPage; 