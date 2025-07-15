const mongoose = require("mongoose");

// Ban subdocument schema
const BanSchema = new mongoose.Schema({
  date: { type: Date, required: true },
  type: { type: String, required: true }, // e.g. 'VAC', 'Game', etc.
});

// Steam profile schema
const ProfileSchema = new mongoose.Schema(
  {
    steamid64: { type: String, required: true, unique: true },
    url: { type: String, required: true },
    bans: [BanSchema],
    avatar_url: { type: String },
    friends: [{ type: String }], // Array of steamid64
  },
  { timestamps: true }
);

module.exports = mongoose.model("Profile", ProfileSchema);
