import { pdfjs } from 'react-pdf';
// This import gives you a URL to the worker
import workerSrc from 'pdfjs-dist/build/pdf.worker.min?worker&url';

pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;