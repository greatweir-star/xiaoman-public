interface ReplyContext {
  reply: {
    text: string;
    emotion?: string;
    isSleeping?: boolean;
  };
  stopPropagation?: boolean;
}

export function nightGuard(context: ReplyContext): void {
  const hour = new Date().getHours();

  if (hour >= 23 || hour < 6) {
    if (Math.random() < 0.1) {
      context.reply.text += "\n（你怎么也还没睡...）";
      return;
    }

    context.reply = {
      text: "我睡了，明天再聊吧~",
      emotion: "困倦",
      isSleeping: true,
    };
    context.stopPropagation = true;
  }
}
