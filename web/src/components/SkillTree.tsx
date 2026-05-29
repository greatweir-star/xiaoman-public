interface Props {
  level: number;
  name: string;
  current: number;
  total: number;
}

export default function SkillTree({ level, name, current, total }: Props) {
  const progress = Math.min((current / total) * 100, 100);

  return (
    <div className="skill-tree">
      <div className="level-badge">Lv.{level}</div>
      <div className="level-name">{name}</div>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <div className="progress-text">
        {current} / {total}
      </div>
    </div>
  );
}
