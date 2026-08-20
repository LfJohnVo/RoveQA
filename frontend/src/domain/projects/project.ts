/** A project, as the UI needs it. */
export interface Project {
  projectId: string;
  name: string;
  defaultRunPolicyId: string | null;
}
