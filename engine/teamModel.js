class Team {
  constructor({ id, name, players, tactic = "balanced" }) {
    this.id = id;
    this.name = name;
    this.players = Array.isArray(players) ? players.slice() : [];
    this.tactic = tactic;
  }

  get outfieldPlayers() {
    return this.players.filter((player) => player.role !== "GK");
  }

  get goalkeeper() {
    return this.players.find((player) => player.role === "GK") || null;
  }

  average(attribute) {
    if (this.players.length === 0) {
      return 0;
    }

    return (
      this.players.reduce((sum, player) => sum + (player[attribute] || 0), 0) /
      this.players.length
    );
  }
}

module.exports = { Team };
