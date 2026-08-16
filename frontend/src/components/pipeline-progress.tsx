type StageState = "waiting" | "active" | "complete" | "error";

export interface PipelineStage {
  name: string;
  detail: string;
  state: StageState;
}

export function PipelineProgress({ stages }: { stages: PipelineStage[] }) {
  return (
    <ol className="pipeline" aria-label="Research pipeline progress">
      {stages.map((stage, index) => (
        <li className={`pipelineStage pipelineStage--${stage.state}`} key={stage.name}>
          <span className="stageNumber">{String(index + 1).padStart(2, "0")}</span>
          <span>
            <strong>{stage.name}</strong>
            <small>{stage.detail}</small>
          </span>
          <span className="stageState" aria-label={stage.state} />
        </li>
      ))}
    </ol>
  );
}
