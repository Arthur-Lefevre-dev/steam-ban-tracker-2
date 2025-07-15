const Redis = require("ioredis");

// Redis queue and set keys
const QUEUE_KEY = "steam:queue";
const SEEN_SET_KEY = "steam:seen";

class RedisQueue {
  /**
   * @param {Redis} redis - Redis client instance
   */
  constructor(redis) {
    this.redis = redis;
  }

  // Add a profile to the queue if not already seen
  async enqueueProfile(steamid64) {
    const added = await this.redis.sadd(SEEN_SET_KEY, steamid64);
    if (added) {
      await this.redis.rpush(QUEUE_KEY, steamid64);
    }
    return added;
  }

  // Get the next profile from the queue
  async dequeueProfile() {
    return await this.redis.lpop(QUEUE_KEY);
  }

  // Check if a profile has already been seen
  async isSeen(steamid64) {
    return await this.redis.sismember(SEEN_SET_KEY, steamid64);
  }
}

module.exports = RedisQueue;
