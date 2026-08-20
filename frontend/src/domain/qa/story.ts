/**
 * A user story and its acceptance criteria.
 *
 * The field that carries the weight is `verificationHint`: a criterion with one gets a
 * deterministic check and can accuse the product; a criterion without one is judged by
 * a model, which leaves the run inconclusive (docs/00). The editor exists largely to
 * make that trade visible while someone is writing the story, rather than as a surprise
 * in a report three runs later.
 */

export interface AcceptanceCriterion {
  criterionId: string;
  description: string;
  /** The literal the page must contain. Its presence is what makes the result
   * reproducible. */
  verificationHint: string | null;
}

export interface UserStory {
  storyId: string;
  projectId: string;
  actor: string;
  goal: string;
  acceptanceCriteria: readonly AcceptanceCriterion[];
}

/** Criteria that can only be judged by a model, and so cannot fail the product. */
export function unverifiable(story: UserStory): AcceptanceCriterion[] {
  return story.acceptanceCriteria.filter((criterion) => criterion.verificationHint === null);
}

/** True when nothing in the story can produce a deterministic answer. */
export function isFullyModelJudged(story: UserStory): boolean {
  return (
    story.acceptanceCriteria.length > 0 &&
    unverifiable(story).length === story.acceptanceCriteria.length
  );
}
