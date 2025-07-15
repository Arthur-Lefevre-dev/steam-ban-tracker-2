const Profile = require("../db/profile.model");
const { scrapeProfile } = require("../services/steamScraper");
const RedisQueue = require("../services/redisQueue");

class SteamBot {
  /**
   * @param {object} options
   * @param {object} options.redis - Redis client instance
   * @param {string} [options.seed] - Optional starting profile (steamid64 or URL)
   */
  constructor({ redis, seed }) {
    this.queue = new RedisQueue(redis);
    this.seed = seed;
    this.running = false;
  }

  // Start the bot loop
  async start() {
    this.running = true;
    if (this.seed) {
      let seedSteamid64 = this.seed;
      // If the seed is not a steamid64, scrape to get the steamid64
      if (!/^\d{17}$/.test(this.seed)) {
        try {
          console.log(`[BOT] Resolving seed to steamid64: ${this.seed}`);
          const data = await require("../services/steamScraper").scrapeProfile(
            this.seed
          );
          seedSteamid64 = data.steamid64;
          console.log(`[BOT] Seed resolved to steamid64: ${seedSteamid64}`);
        } catch (err) {
          console.error(`[BOT] Failed to resolve seed: ${err.message}`);
          return;
        }
      }
      console.log(`[BOT] Seeding queue with: ${seedSteamid64}`);
      await this.queue.enqueueProfile(seedSteamid64);
    }
    while (this.running) {
      const steamid64 = await this.queue.dequeueProfile();
      if (!steamid64) {
        console.log("[BOT] Queue empty, waiting...");
        await new Promise((res) => setTimeout(res, 1000)); // Wait if queue is empty
        continue;
      }
      console.log(`[BOT] Processing profile: ${steamid64}`);
      try {
        // Scrape profile
        const data = await scrapeProfile(steamid64);
        console.log(`[BOT] Scraped profile: ${data.steamid64}`);
        // Save to MongoDB (upsert)
        await Profile.findOneAndUpdate({ steamid64: data.steamid64 }, data, {
          upsert: true,
          new: true,
        });
        console.log(`[BOT] Saved profile to DB: ${data.steamid64}`);
        // Enqueue friends
        for (const friendId of data.friends) {
          const added = await this.queue.enqueueProfile(friendId);
          if (added) {
            console.log(`[BOT] Added friend to queue: ${friendId}`);
          }
        }
        // Wait a random delay (1-3 seconds) before next profile to simulate human behavior
        const delay = Math.floor(Math.random() * 2000) + 1000; // 1000ms to 3000ms
        console.log(`[BOT] Waiting ${delay}ms before next profile...`);
        await new Promise((res) => setTimeout(res, delay));
      } catch (err) {
        if (err.response && err.response.status === 429) {
          console.error(
            `[BOT] Rate limited (429). Waiting 1 minute before continuing...`
          );
          await new Promise((res) => setTimeout(res, 60000));
        } else {
          console.error(`[BOT] Error scraping ${steamid64}:`, err.message);
        }
      }
    }
  }

  // Stop the bot
  stop() {
    this.running = false;
  }
}

module.exports = SteamBot;
