const axios = require("axios");
const cheerio = require("cheerio");

// Create an axios instance with realistic browser headers
const axiosInstance = axios.create({
  headers: {
    // Use a common Chrome User-Agent
    "User-Agent":
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    Accept:
      "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    Connection: "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    // Add more headers if needed
  },
});

/**
 * Scrape a Steam profile page and extract required information.
 * @param {string} urlOrSteamid64 - Steam profile URL or steamid64
 * @returns {Promise<{steamid64: string, url: string, bans: Array<{type: string, date: Date}>, avatar_url: string, friends: string[]}>}
 */
async function scrapeProfile(urlOrSteamid64) {
  // Build the profile URL if only steamid64 is provided
  let url = urlOrSteamid64;
  if (/^\d{17}$/.test(urlOrSteamid64)) {
    url = `https://steamcommunity.com/profiles/${urlOrSteamid64}`;
  }
  // Use the axios instance with browser headers
  const res = await axiosInstance.get(url);
  const $ = cheerio.load(res.data);

  // Extract steamid64 from URL or from HTML if not present
  let steamid64 = null;
  const urlMatch = url.match(/\d{17}/);
  if (urlMatch) {
    steamid64 = urlMatch[0];
  } else {
    // Try to find steamid64 in the HTML (in links or scripts)
    // Example: <a href="https://steamcommunity.com/profiles/76561198012345678">...
    const profileLink = $("a[href*='/profiles/']").attr("href");
    const htmlMatch = profileLink && profileLink.match(/\d{17}/);
    if (htmlMatch) {
      steamid64 = htmlMatch[0];
    } else {
      // Try to find in scripts (sometimes present in JSON)
      const html = res.data;
      const scriptMatch = html.match(/"steamid"\s*:\s*"(\d{17})"/);
      if (scriptMatch) {
        steamid64 = scriptMatch[1];
      }
    }
  }
  if (!steamid64) {
    throw new Error("Could not extract steamid64 from profile");
  }

  // Extract avatar URL
  const avatar_url = $(".playerAvatarAutoSizeInner img").attr("src") || "";

  // Extract bans (VAC/Game bans)
  let bans = [];
  const banText = $(".profile_ban_status").text();
  if (banText) {
    // Example: "1 VAC ban on record | Info | 123 days since last ban"
    const vacMatch = banText.match(/(\d+) VAC ban/);
    if (vacMatch) {
      // Try to extract date info if present
      const daysMatch = banText.match(/(\d+) days since last ban/);
      let date = null;
      if (daysMatch) {
        const daysAgo = parseInt(daysMatch[1], 10);
        date = new Date(Date.now() - daysAgo * 24 * 60 * 60 * 1000);
      }
      bans.push({ type: "VAC", date });
    }
  }

  // Extract friends from the /friends/ page
  let friends = [];
  try {
    const friendsUrl = `https://steamcommunity.com/profiles/${steamid64}/friends/`;
    const friendsRes = await axiosInstance.get(friendsUrl);
    const $friends = cheerio.load(friendsRes.data);
    // For each friend block, get the data-steamid attribute
    $friends("div.selectable.friend_block_v2").each((i, el) => {
      const steamid = $friends(el).attr("data-steamid");
      if (steamid) friends.push(steamid);
    });
  } catch (err) {
    // If the friends page is private or unavailable, just return an empty list
    // Log in English for debug
    console.error(
      `[SCRAPER] Could not fetch friends for ${steamid64}:`,
      err.message
    );
  }

  return {
    steamid64,
    url,
    bans,
    avatar_url,
    friends,
  };
}

module.exports = { scrapeProfile };
