import { buildQrUrl } from "../../api/client";
import styles from "./QrPanel.module.css";

interface QrPanelProps {
  /** The short code whose QR code to preview and download. */
  shortCode: string;
}

/**
 * Shows the link's QR code as a preview and offers PNG and SVG downloads. The QR endpoint
 * is same-origin, so the `download` attribute saves the file instead of navigating to it.
 */
export default function QrPanel({ shortCode }: QrPanelProps) {
  const previewUrl = buildQrUrl(shortCode, "png");

  return (
    <div className={styles.panel} id="qr-panel">
      <span className={styles.heading} id="qr-panel-heading">
        QR code
      </span>
      <div className={styles.preview} id="qr-preview">
        <img
          className={styles.previewImage}
          id="qr-preview-image"
          src={previewUrl}
          alt={`QR code for the short link ${shortCode}`}
          width={160}
          height={160}
        />
      </div>
      <div className={styles.downloads} id="qr-downloads">
        <a
          className={styles.downloadButton}
          id="qr-download-png"
          href={previewUrl}
          download={`${shortCode}-qr.png`}
        >
          Download PNG
        </a>
        <a
          className={styles.downloadButton}
          id="qr-download-svg"
          href={buildQrUrl(shortCode, "svg")}
          download={`${shortCode}-qr.svg`}
        >
          Download SVG
        </a>
      </div>
    </div>
  );
}
