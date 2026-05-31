import styles from "./TotalClicks.module.css";

interface TotalClicksProps {
  totalClicks: number;
}

/** The headline total-clicks stat for a link. */
export default function TotalClicks({ totalClicks }: TotalClicksProps) {
  return (
    <section
      className={styles.card}
      id="analytics-total-clicks"
      aria-labelledby="analytics-total-clicks-label"
    >
      <span className={styles.label} id="analytics-total-clicks-label">
        Total clicks
      </span>
      <span className={styles.value} id="analytics-total-clicks-value">
        {totalClicks.toLocaleString()}
      </span>
    </section>
  );
}
