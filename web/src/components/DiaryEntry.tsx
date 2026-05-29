interface Props {
  date: string;
  content: string;
  locked?: boolean;
}

export default function DiaryEntry({ date, content, locked }: Props) {
  if (locked) {
    return (
      <div className="diary-entry locked">
        <div className="diary-date">{date}</div>
        <div className="diary-lock">🔒 亲密度不足，还不能看哦</div>
      </div>
    );
  }

  return (
    <div className="diary-entry">
      <div className="diary-date">{date}</div>
      <div className="diary-content">{content}</div>
    </div>
  );
}
