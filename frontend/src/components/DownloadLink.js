import React from 'react';

const DownloadLink = ({ docxPath }) => (
  <p>
    ✅ Done! <a href={docxPath} download>Download your DOCX</a>
  </p>
);

export default DownloadLink;