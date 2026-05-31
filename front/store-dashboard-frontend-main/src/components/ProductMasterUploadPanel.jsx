import { useMemo, useState } from "react";
import { uploadProductMaster } from "../api/api";

function ProductMasterUploadPanel() {
  const [files, setFiles] = useState([]);
  const [dryRun, setDryRun] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const canSubmit = useMemo(() => files.length > 0 && !loading, [files, loading]);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (files.length === 0) {
      setError("Select one or more product master CSV files.");
      return;
    }

    setError("");
    setResult(null);
    setLoading(true);

    try {
      const response = await uploadProductMaster({ files, dryRun });
      setResult(response);
    } catch (err) {
      setError("Product master upload failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">MASTER</span>
          <h2>Product master upload</h2>
        </div>
      </div>

      <p className="panel-desc">
        Upload the category master CSV files first. The CSV file name becomes the product category,
        and PLU codes are saved for inventory category matching.
      </p>

      <form className="sales-upload-form" onSubmit={handleSubmit}>
        <label className="sales-upload-field">
          <span>Master CSV files</span>
          <input
            type="file"
            accept=".csv"
            multiple
            onChange={(event) => setFiles(Array.from(event.target.files || []))}
          />
          <small>{files.length > 0 ? `${files.length} files selected` : "No files selected"}</small>
        </label>

        <label className="sales-upload-checkbox">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(event) => setDryRun(event.target.checked)}
          />
          <span>DRY RUN (save nothing, test only)</span>
        </label>

        <div className="sales-upload-actions">
          <button className="sales-upload-button" type="submit" disabled={!canSubmit}>
            {loading ? "Processing..." : dryRun ? "Run dry run" : "Save master"}
          </button>
        </div>
      </form>

      {error && <p className="panel-error">Failed: {error}</p>}

      {result && (
        <div className="sales-upload-result">
          <h3>Result</h3>
          <div className="sales-upload-status success">
            <strong>Success</strong>
            <span>{dryRun ? "Test completed successfully." : "Product master upload completed."}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProductMasterUploadPanel;
