class Player {
  constructor({
    id,
    name,
    role,
    passing = 60,
    shooting = 60,
    tackling = 60,
    positioning = 60,
    composure = 60,
  }) {
    this.id = id;
    this.name = name || id;
    this.role = role || "MF";
    this.passing = passing;
    this.shooting = shooting;
    this.tackling = tackling;
    this.positioning = positioning;
    this.composure = composure;
  }

  get overall() {
    return (
      this.passing +
      this.shooting +
      this.tackling +
      this.positioning +
      this.composure
    ) / 5;
  }
}

module.exports = { Player };
