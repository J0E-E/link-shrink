import styles from "./MetricStat.module.css";

export type MetricTone = "default" | "success" | "warning";

interface MetricStatProps {
  id: string;
  label: string;
  value: string;
  hint?: string;
  tone?: MetricTone;
}

const TONE_CLASS: Record<MetricTone, string> = {
  default: "",
  success: styles.valueSuccess,
  warning: styles.valueWarning,
};

/** A single live-metric stat card: a big value, a label, and an optional hint line. */
export default function MetricStat({ id, label, value, hint, tone = "default" }: MetricStatProps) {
  const valueClassName = `${styles.value} ${TONE_CLASS[tone]}`.trim();

  return (
    <div className={styles.stat} id={id}>
      <span className={valueClassName} id={`${id}-value`}>
        {value}
      </span>
      <span className={styles.label} id={`${id}-label`}>
        {label}
      </span>
      {hint && (
        <span className={styles.hint} id={`${id}-hint`}>
          {hint}
        </span>
      )}
    </div>
  );
}
