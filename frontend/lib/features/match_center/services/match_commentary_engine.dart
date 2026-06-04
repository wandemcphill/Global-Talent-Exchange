import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';

class MatchCommentaryEngine {
  const MatchCommentaryEngine._();

  static String lineForEvent(MatchEvent event, {MatchTimelineFrame? frame}) {
    final String explicit = event.commentary.trim();
    if (explicit.isNotEmpty) {
      return explicit;
    }
    return lineForRaw(
      eventType: event.type.name,
      player: event.primaryPlayerName ?? event.secondaryPlayerName,
      team: event.teamName,
      score: '${event.homeScore}-${event.awayScore}',
      minute: event.minute,
      title: event.bannerText,
      isCloseScore: _scoresAreClose(event.homeScore, event.awayScore),
    );
  }

  static String lineForRaw({
    required String eventType,
    String? player,
    String? team,
    String? score,
    int? minute,
    String? title,
    bool? isCloseScore,
  }) {
    final String type = _normalizeEventType(eventType);
    final String? playerLabel = _clean(player);
    final String? teamLabel = _clean(team);
    final String? titleLabel = _clean(title);
    final bool lateClose =
        (minute ?? 0) >= 86 && (isCloseScore ?? _scoreTextIsClose(score));

    if (lateClose && type != 'halftime' && type != 'fulltime') {
      if (type == 'goal') {
        return _withScore(
          '${_actor(playerLabel, teamLabel)} lands a huge late goal.',
          score,
        );
      }
      return _withScore(
        teamLabel == null
            ? 'Late drama unfolding.'
            : 'Late drama unfolding as $teamLabel push again.',
        score,
      );
    }

    switch (type) {
      case 'goal':
        return _withScore(
          '${_actor(playerLabel, teamLabel)} finds the net. What a finish!',
          score,
        );
      case 'miss':
        return _withScore(
          '${_actor(playerLabel, teamLabel)} misses a big chance.',
          score,
        );
      case 'save':
        return _withScore(
          '${_actor(playerLabel, teamLabel)} is denied by the keeper.',
          score,
        );
      case 'foul':
        return _withScore(
          teamLabel == null
              ? 'The referee stops play for a foul.'
              : '$teamLabel concede a foul and the tempo breaks.',
          score,
        );
      case 'red_card':
        return _withScore(
          '${_actor(playerLabel, teamLabel)} is sent off.',
          score,
        );
      case 'yellow_card':
      case 'card':
        return _withScore(
          '${_actor(playerLabel, teamLabel)} goes into the book.',
          score,
        );
      case 'substitution':
        return _withScore(
          teamLabel == null
              ? 'Fresh legs are coming on.'
              : '$teamLabel make a change.',
          score,
        );
      case 'pass':
        return _withScore(
          '${_actor(playerLabel, teamLabel)} keeps the move alive.',
          score,
        );
      case 'attack':
        return _withScore(
          teamLabel == null
              ? 'The attack starts to gather speed.'
              : '$teamLabel build pressure in the final third.',
          score,
        );
      case 'offside':
        return _withScore('The flag goes up for offside.', score);
      case 'kickoff':
        return 'We are underway.';
      case 'halftime':
        return _withScore('The players head in at half-time.', score);
      case 'fulltime':
        return _withScore('Full-time. The match is complete.', score);
      default:
        if (titleLabel != null) {
          return _withScore(_ensureSentence(titleLabel), score);
        }
        return fallbackForFrame(null);
    }
  }

  static String fallbackForFrame(MatchTimelineFrame? frame) {
    if (frame == null) {
      return 'The match is settling into shape.';
    }
    if (frame.clockMinute >= 86 &&
        _scoresAreClose(frame.homeScore, frame.awayScore)) {
      return 'Late drama unfolding with the score still tight.';
    }
    switch (frame.possessionPhase) {
      case MatchPossessionPhase.boxAttack:
        return 'The ball is in the danger area now.';
      case MatchPossessionPhase.finalThird:
        return 'The attack is asking real questions in the final third.';
      case MatchPossessionPhase.transition:
        return 'Space opens up as the transition breaks forward.';
      case MatchPossessionPhase.setPiece:
      case MatchPossessionPhase.restart:
        return 'Players are setting their runs for the restart.';
      case MatchPossessionPhase.buildUp:
        return 'The possession shape is forming from the back.';
      case MatchPossessionPhase.recovery:
        return 'The ball is recovered and the shape resets.';
      case MatchPossessionPhase.stoppage:
      case MatchPossessionPhase.deadBall:
        return 'Play pauses while the teams reorganize.';
      case MatchPossessionPhase.attack:
        return 'The attack is starting to stretch the pitch.';
      case MatchPossessionPhase.control:
      case null:
        return 'The match is settling into shape.';
    }
  }

  static String _actor(String? player, String? team) {
    if (player != null) {
      return player;
    }
    if (team != null) {
      return team;
    }
    return 'The chance';
  }

  static String _normalizeEventType(String value) {
    final String expanded =
        value
            .trim()
            .replaceAll('-', '_')
            .replaceAllMapped(
              RegExp(r'([a-z0-9])([A-Z])'),
              (Match match) => '${match.group(1)}_${match.group(2)}',
            )
            .toLowerCase();
    return expanded == 'redcard'
        ? 'red_card'
        : expanded == 'yellowcard'
        ? 'yellow_card'
        : expanded;
  }

  static String _withScore(String text, String? score) {
    final String sentence = _ensureSentence(text);
    final String? scoreLabel = _clean(score);
    if (scoreLabel == null) {
      return sentence;
    }
    return '$sentence Score: $scoreLabel.';
  }

  static String _ensureSentence(String text) {
    final String trimmed = text.trim();
    if (trimmed.isEmpty) {
      return 'The match is settling into shape.';
    }
    if (trimmed.endsWith('.') ||
        trimmed.endsWith('!') ||
        trimmed.endsWith('?')) {
      return trimmed;
    }
    return '$trimmed.';
  }

  static String? _clean(String? value) {
    final String text = (value ?? '').trim();
    return text.isEmpty ? null : text;
  }

  static bool _scoreTextIsClose(String? value) {
    final String? score = _clean(value);
    if (score == null) {
      return false;
    }
    final List<String> parts = score.split(RegExp(r'\s*[-:]\s*'));
    if (parts.length != 2) {
      return false;
    }
    final int? home = int.tryParse(parts.first);
    final int? away = int.tryParse(parts.last);
    if (home == null || away == null) {
      return false;
    }
    return _scoresAreClose(home, away);
  }

  static bool _scoresAreClose(int home, int away) {
    return (home - away).abs() <= 1;
  }
}
