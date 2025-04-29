import React from 'react';
import {
    Typography,
    Box,
    Tooltip,
    Link,
    ListItemIcon,
    Collapse,
    IconButton,
    Chip
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import InfoIcon from '@mui/icons-material/Info';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { ProcessingResult, ResultStatus, FoundEmailData } from '../types';

interface ResultDisplayProps {
  result: ProcessingResult;
}

const getPrimaryVerificationInfo = (result: ProcessingResult): { status?: boolean | null, message?: string } => {
    if (!result.email || !result.email_discovery_results) {
        return {};
    }
    const primaryEmailData = result.email_discovery_results.found_emails.find(e => e.email === result.email);
    return {
        status: primaryEmailData?.verification_status,
        message: primaryEmailData?.verification_message
    };
};

// Get status info: Use Tailwind colors/classes instead of MUI severity/color strings where possible
const getStatusInfo = (result: ProcessingResult): { status: ResultStatus; icon: React.ReactElement; alertClass: string; message: string } => {
    const primaryVerification = getPrimaryVerificationInfo(result);
    // Define Tailwind classes for different alert types
    const baseAlertClass = "p-4 rounded-md border mb-4 flex items-start";
    const successClass = `${baseAlertClass} bg-green-50 border-green-300 text-green-700`;
    const warningClass = `${baseAlertClass} bg-yellow-50 border-yellow-300 text-yellow-700`;
    const errorClass = `${baseAlertClass} bg-red-50 border-red-300 text-red-700`;
    const infoClass = `${baseAlertClass} bg-blue-50 border-blue-300 text-blue-700`; // Use blue for info/not found

    if (result.email_finding_error) {
        return { status: ResultStatus.Error, icon: <ErrorIcon className="mr-2 h-5 w-5"/>, alertClass: errorClass, message: result.email_finding_error };
    }
    if (result.email_finding_skipped) {
        return { status: ResultStatus.Skipped, icon: <InfoIcon className="mr-2 h-5 w-5"/>, alertClass: warningClass, message: result.email_finding_reason || 'Processing skipped' };
    }
    if (result.email) {
        if (primaryVerification.status === true) {
             return { status: ResultStatus.Verified, icon: <CheckCircleIcon className="mr-2 h-5 w-5"/>, alertClass: successClass, message: primaryVerification.message || 'Email found and verified' };
        } else if (primaryVerification.status === false) {
             return { status: ResultStatus.Rejected, icon: <WarningIcon className="mr-2 h-5 w-5"/>, alertClass: warningClass, message: primaryVerification.message || 'Email found but rejected by server' };
        }
        return { status: ResultStatus.Success, icon: <CheckCircleIcon className="mr-2 h-5 w-5"/>, alertClass: successClass, message: primaryVerification.message || 'Email found (verification inconclusive)' };
    }
    return { status: ResultStatus.NotFound, icon: <HelpOutlineIcon className="mr-2 h-5 w-5"/>, alertClass: infoClass, message: 'No high-confidence email address found.' };
};

const ResultDisplay: React.FC<ResultDisplayProps> = ({ result }) => {
  const { status, icon, alertClass, message } = getStatusInfo(result);
  const [detailsOpen, setDetailsOpen] = React.useState(false);

  const toggleDetails = () => setDetailsOpen(!detailsOpen);

  const renderVerificationStatus = (emailData?: FoundEmailData) => {
    if (!emailData) return null;
    let iconElement = <HelpOutlineIcon fontSize="inherit" className="inline-block align-middle mr-1 h-4 w-4"/>;
    let text = emailData.verification_message || 'Inconclusive';
    let textColorClass = 'text-gray-500';

    if (emailData.verification_status === true) {
        iconElement = <CheckCircleIcon fontSize="inherit" className="inline-block align-middle mr-1 h-4 w-4 text-green-500"/>;
        text = emailData.verification_message || 'Verified';
        textColorClass = 'text-green-600';
    } else if (emailData.verification_status === false) {
        iconElement = <WarningIcon fontSize="inherit" className="inline-block align-middle mr-1 h-4 w-4 text-yellow-500"/>;
        text = emailData.verification_message || 'Rejected';
        textColorClass = 'text-yellow-600';
    }

    return (
        <Tooltip title={text}>
            {/* Use span with Tailwind classes */}
            <span className={`text-xs inline-flex items-center ${textColorClass}`}>
                {iconElement}
                {text.length > 30 ? `${text.substring(0, 27)}...` : text}
            </span>
        </Tooltip>
    );
  }

  return (
    // Main container with Tailwind styles
    <div className="bg-white shadow-md rounded-lg p-4 md:p-6 mt-4">
      {/* Alert using div and Tailwind classes */}
      <div className={alertClass}>
          {icon}
          <div>
              <Typography variant="h6" component="p" className="font-semibold">{status}</Typography>
              {/* Show detailed message only if relevant */} 
              {(status === ResultStatus.Error || status === ResultStatus.Skipped || status === ResultStatus.Rejected || (status === ResultStatus.Success && message !== 'Email found (verification inconclusive)')) &&
                <Typography variant="body2" className="text-sm">{message}</Typography>
              }
          </div>
      </div>

      {/* Grid using Tailwind flexbox/grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
                <h3 className="text-sm font-medium text-gray-500 mb-1">Input:</h3>
                <p className="text-sm text-gray-800 break-words">
                    Name: {result.contact_input.full_name || `${result.contact_input.first_name || ''} ${result.contact_input.last_name || ''}`.trim()}
                </p>
                <p className="text-sm text-gray-800 break-words">
                    Domain/Website: {result.contact_input.domain}
                </p>
          </div>
          {result.email && (
             <div>
                 <h3 className="text-sm font-medium text-gray-500 mb-1">Most Likely Email:</h3>
                 <Link href={`mailto:${result.email}`} className="text-base text-blue-600 hover:text-blue-800 font-medium break-words block mb-1">
                     {result.email}
                 </Link>
                 {/* Use Flexbox for confidence and verification */}
                 <div className="flex items-center space-x-2 flex-wrap">
                     <Tooltip title="Likelihood score (0-10)">
                         {/* Keep MUI Chip for now, or replace with styled div */}
                          <Chip 
                             label={`Confidence: ${result.email_confidence ?? 'N/A'}/10`} 
                             size="small" 
                             variant="outlined"
                             className="text-xs !bg-gray-100 !border-gray-300"
                           />
                     </Tooltip>
                     {renderVerificationStatus(result.email_discovery_results?.found_emails.find(e => e.email === result.email))}
                 </div>
             </div>
          )}
      </div>

      {(result.email_alternatives.length > 0 || result.email_discovery_results) && (
           <hr className="my-4 border-gray-200"/>
      )}

      {/* Alternatives List using Tailwind */}
      {result.email_alternatives.length > 0 && (
        <div className="mb-4">
           <h4 className="text-sm font-medium text-gray-500 mb-1">Alternatives Found:</h4>
           <ul className="list-none pl-0 space-y-1">
            {result.email_alternatives.map((alt, index) => (
                <li key={index} className="text-sm text-gray-800 flex justify-between items-center">
                    <span className="break-all">{alt}</span>
                    <span className="ml-2 flex-shrink-0">
                         {renderVerificationStatus(result.email_discovery_results?.found_emails.find(e => e.email === alt))} 
                    </span>
                </li>
            ))}
           </ul>
        </div>
      )}

      {/* Detailed Discovery Results (Collapsible) */}
      {result.email_discovery_results && (
        <div>
             <button
                  onClick={toggleDetails}
                  className="text-sm text-blue-600 hover:text-blue-800 flex items-center"
              >
                  {detailsOpen ? 'Hide Details' : 'Show Discovery Details'}
                  {detailsOpen ? <ExpandLessIcon className="ml-1 h-4 w-4"/> : <ExpandMoreIcon className="ml-1 h-4 w-4"/>}
              </button>
              <Collapse in={detailsOpen} timeout="auto" unmountOnExit>
                 <div className="mt-2 pl-4 border-l-2 border-gray-200 text-xs text-gray-600 space-y-1">
                     {result.email_discovery_results.methods_used.length > 0 && (
                        <p>
                            <span className="font-medium">Methods:</span> {result.email_discovery_results.methods_used.join(', ')}
                        </p>
                     )}
                     {Object.keys(result.email_discovery_results.verification_log || {}).length > 0 && (
                        <div className="mt-1">
                            <p className="font-medium">Verification Log:</p>
                            <ul className="list-none pl-2">
                                {Object.entries(result.email_discovery_results.verification_log).map(([email, logMsg], idx) => (
                                    <li key={idx} className="break-words">
                                        {email}: {logMsg}
                                    </li>
                                ))}
                            </ul>
                         </div>
                     )}
                 </div>
              </Collapse>
         </div>
      )}

       {result.processing_time_ms !== null && result.processing_time_ms !== undefined && (
            <p className="text-xs text-gray-500 mt-4 pt-2 border-t border-gray-200">
               Processing Time: {result.processing_time_ms.toFixed(2)} ms
            </p>
       )}

    </div>
  );
};

export default ResultDisplay; 