import type { LinkView } from "../../api/types";
import LinkCard from "./LinkCard";
import styles from "./LinkList.module.css";

interface LinkListProps {
  links: LinkView[];
}

/** The dashboard feed of links, rendered as a single-column list of cards. */
export default function LinkList({ links }: LinkListProps) {
  return (
    <ul className={styles.list} id="dashboard-link-list">
      {links.map((link) => (
        <LinkCard key={link.short_code} link={link} />
      ))}
    </ul>
  );
}
