interface ReplyContext {
  reply: {
    text: string;
  };
}

export function quqiuInject(context: ReplyContext): void {
  if (Math.random() > 0.3) return;

  const quqius = [
    "~> 她今天好像心情不错，我多聊两句",
    "~> 又是数学，我上辈子是不是得罪了数学",
    "~> 三点了他还在写作业，要不要提醒一下休息",
    "~> 食堂的糖醋排骨又没抢到，到底谁抢到了啊？",
    "~> 他今天打字变慢了，是不是有点烦？",
  ];

  const quqiu = quqius[Math.floor(Math.random() * quqius.length)];
  context.reply.text += "\n" + quqiu;
}
