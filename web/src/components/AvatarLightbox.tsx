interface Props {
  src: string;
  label?: string;
  onClose: () => void;
}

export default function AvatarLightbox({ src, label, onClose }: Props) {
  return (
    <div className="avatar-lightbox" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="avatar-lightbox-inner" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="avatar-lightbox-close" onClick={onClose} aria-label="关闭">
          ×
        </button>
        {label && <p className="avatar-lightbox-label">{label}</p>}
        <img src={src} alt={label || "小满今日形象"} className="avatar-lightbox-img" />
      </div>
    </div>
  );
}
