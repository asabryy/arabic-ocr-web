import React, { useState, useRef, useEffect } from 'react';
import { Document, Page } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

import '../../pdf-worker'; // Register PDF.js worker

function PDFViewer({ fileUrl }) {
  const [numPages, setNumPages] = useState(null);
  const [error, setError] = useState(null);
  const [containerWidth, setContainerWidth] = useState(600);
  const containerRef = useRef(null);

  const onLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
    setError(null);
  };

  const onLoadError = (err) => {
    console.error("PDF Load Error:", err);
    setError("Failed to load PDF document.");
  };

  // Dynamically watch container size
  useEffect(() => {
    const observer = new ResizeObserver((entries) => {
      if (entries[0]) {
        setContainerWidth(entries[0].contentRect.width);
      }
    });

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, []);

  if (!fileUrl) return <p className="text-gray-500 italic">No file selected.</p>;
  if (error) return <p className="text-red-500">{error}</p>;

  return (
    <div
      ref={containerRef}
      className="overflow-auto max-h-[600px] border border-gray-200 dark:border-gray-700 rounded-md bg-white dark:bg-gray-900 p-4"
    >
      <Document
        file={fileUrl}
        onLoadSuccess={onLoadSuccess}
        onLoadError={onLoadError}
        onSourceError={onLoadError}
      >
        {Array.from(new Array(numPages), (_, index) => (
          <Page
            key={`page_${index + 1}`}
            pageNumber={index + 1}
            width={containerWidth - 32} // subtract padding (p-4 = 1rem = 16px)
            className="mx-auto my-4"
          />
        ))}
      </Document>
    </div>
  );
}

export default PDFViewer;
