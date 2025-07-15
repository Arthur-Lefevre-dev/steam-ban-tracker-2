// Load environment variables
require("dotenv").config();

const mongoose = require("mongoose");
const Redis = require("ioredis");
const SteamBot = require("./bots/steamBot");

// MongoDB connection
async function connectMongo() {
  try {
    // Connect to MongoDB without deprecated options
    await mongoose.connect(process.env.MONGO_URI);
    console.log("MongoDB connected");
  } catch (err) {
    console.error("MongoDB connection error:", err);
    process.exit(1);
  }
}

// Redis connection
function connectRedis() {
  const redis = new Redis(process.env.REDIS_URL);
  redis.on("connect", () => console.log("Redis connected"));
  redis.on("error", (err) => console.error("Redis error:", err));
  return redis;
}

// Main entry point
(async () => {
  await connectMongo();
  const redis = connectRedis();
  // Get seed from command line argument if provided
  const seed = process.argv[2];
  const bot = new SteamBot({ redis, seed });
  await bot.start();
})();
