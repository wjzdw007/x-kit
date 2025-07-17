import fs from "fs-extra";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { OpenAI } from "openai";
import { execSync } from "child_process";
import path from "path";

dayjs.extend(utc);

// 配置 OpenAI API
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  baseURL: "https://openrouter.ai/api/v1", // 这里替换成你的实际域名
});

const model = "openai/gpt-4.1";

interface TweetData {
  user: {
    screenName: string;
    name: string;
  };
  fullText: string;
  createdAt: string;
  tweetUrl: string;
  images: string[];
  videos: string[];
}

async function summarizeElonDaily() {
  try {
    // 获取今天的日期（UTC）
    const today = dayjs().utc().format("YYYY-MM-DD");
    // const today = "2025-07-16";
    const filePath = `./tweets/${today}.json`;

    // 检查文件是否存在
    if (!fs.existsSync(filePath)) {
      console.log(`今天的推文文件不存在: ${filePath}`);
      return;
    }

    // 读取推文数据
    const tweets: TweetData[] = JSON.parse(fs.readFileSync(filePath, "utf-8"));

    if (tweets.length === 0) {
      console.log("今天没有推文数据");
      return;
    }

    // 过滤出 elon 的推文
    const elonTweets = tweets.filter(tweet =>
      tweet.user.screenName.toLowerCase() === "elonmusk"
    );

    if (elonTweets.length === 0) {
      console.log("今天没有找到 Elon 的推文");
      return;
    }

    // 整理推文内容
    const tweetSummaries = elonTweets.map((tweet, index) => {
      const time = dayjs.utc(tweet.createdAt).format("HH:mm");
      const hasImages = tweet.images && tweet.images.length > 0;
      const hasVideos = tweet.videos && tweet.videos.length > 0;
      let mediaInfo = '';
      if (hasImages && hasVideos) {
        mediaInfo = ` [包含${tweet.images.length}张图片, ${tweet.videos.length}个视频]`;
      } else if (hasImages) {
        mediaInfo = ` [包含${tweet.images.length}张图片]`;
      } else if (hasVideos) {
        mediaInfo = ` [包含${tweet.videos.length}个视频]`;
      }
      const urlInfo = tweet.tweetUrl ? `\n链接: ${tweet.tweetUrl}` : '';
      return `${index + 1}. [${time}] ${tweet.fullText}${mediaInfo}${urlInfo}`;
    }).join("\n");

    // 构造提示词
    const prompt = `这是我抓取的马斯克的推文，帮我看看这家伙今天都干了啥。总结一下，尽量简洁一些，如果引用原来的推文，请附带原文链接。

---
今天的推文内容：
${tweetSummaries}
`;

    // 保存推文内容到文件，方便手动发送给大模型
    const outputPath = `./summaries/${today}-elon-tweets.txt`;
    await fs.ensureDir("./summaries");
    fs.writeFileSync(outputPath, prompt);

    // 自动调用 OpenAI API 进行总结
    console.log("正在调用大模型生成总结...");
    const completion = await openai.chat.completions.create({
      model: model,
      messages: [
        {
          role: "user",
          content: prompt
        }
      ],
    //   temperature: 0.7,
    //   max_tokens: 64000
    });
    const summary = completion.choices[0].message.content;

    // 保存总结内容到 markdown 文件
    const summaryPath = `./summaries/${today}-elon-summary.md`;
    const summaryContent = `# Elon Musk 今日行为总结 (${today})

${summary}

---
*生成时间: ${dayjs().format("YYYY-MM-DD HH:mm:ss")}*
*推文数量: ${elonTweets.length}*
*模型: ${model}*
`;
    fs.writeFileSync(summaryPath, summaryContent);

    // 输出到控制台
    console.log("=".repeat(50));
    console.log(`Elon Musk 今日行为总结 (${today})`);
    console.log("=".repeat(50));
    console.log(summary);
    console.log("=".repeat(50));
    console.log(`总结已保存到: ${summaryPath}`);

    // 自动上传到独立仓库
    try {
      const summariesDir = "./summaries";
      const repoUrl = process.env.ELON_DAILY_SUMMARY_REPO_URL!;
      
      // 检查 summaries 目录是否存在
      if (!fs.existsSync(summariesDir)) {
        console.log("summaries 目录不存在");
        return;
      }
      
      // 进入 summaries 目录
      process.chdir(summariesDir);
      
      // 检查是否已经是 Git 仓库
      if (!fs.existsSync(".git")) {
        // 初始化 Git 仓库
        execSync("git init");
        execSync(`git remote add origin ${repoUrl}`);
      }
      
      // 添加文件并提交
      execSync("git add .");
      execSync(`git commit -m "feat: 添加 ${today} Elon 行为总结"`);
      execSync("git push origin master");
      
      console.log("总结已上传到独立仓库");
      
      // 回到原目录
      process.chdir("..");
      
    } catch (error) {
      console.error("自动上传失败:", error);
    }

  } catch (error) {
    console.error("分析过程中出现错误:", error);
  }
}

// 执行分析
summarizeElonDaily(); 