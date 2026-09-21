import { Badge } from '../../components/ui/Badge';
import styles from './DemoDatasetBanner.module.css';

/** Renders at the top of every Risk Analysis screen. Deliberately a
 * distinct visual treatment from InsightCallout (amber notice box, not
 * the cyan "algorithmic intelligence" accent) so this module can never
 * be visually mistaken for Module 1/2's real baseline-panel views — see
 * MODULE3_REFERENCE.md: "unmistakably, persistently labeled... never
 * conflated with the Module 1/2 baseline panel."
 */
export function DemoDatasetBanner() {
  return (
    <div className={styles.banner} role="note">
      <Badge tone="medium">Demonstration dataset</Badge>
      <p className={`${styles.text} text-body-md`}>
        A real trained model (scikit-learn + SHAP) running on a separate, entirely synthetic
        workforce built to demonstrate the ML pipeline end to end. This is not the Employee
        Directory or Workforce Health baseline panel — none of these people or outcomes are
        real, and this model has not been validated against real LS Digital attrition. See
        MODULE3_REFERENCE.md.
      </p>
    </div>
  );
}
