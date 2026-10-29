import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/ambient_audio_controller.dart';
import '../../services/audio/gtex_audio_context.dart';
import '../../services/audio/gtex_track_metadata.dart';
import '../../ui_gtex/components/gtex_button.dart';
import '../../ui_gtex/components/gtex_panel.dart';
import '../../ui_gtex/theme/gtex_colors.dart';
import '../../ui_gtex/theme/gtex_spacing.dart';

class GtexAudioSettingsSheet extends StatefulWidget {
  const GtexAudioSettingsSheet({
    super.key,
    required this.controller,
  });

  final AmbientAudioState controller;

  static Future<void> show(BuildContext context, AmbientAudioState controller) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: GtexColors.panel,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(GtexSpacing.radiusLg)),
      ),
      builder: (BuildContext context) => GtexAudioSettingsSheet(controller: controller),
    );
  }

  @override
  State<GtexAudioSettingsSheet> createState() => _GtexAudioSettingsSheetState();
}

class _GtexAudioSettingsSheetState extends State<GtexAudioSettingsSheet> {
  bool _showCredits = false;

  Future<void> _openExternalUrl(String? rawUrl) async {
    if (rawUrl == null || rawUrl.isEmpty) return;
    final Uri uri = Uri.parse(rawUrl);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (BuildContext context, Widget? child) {
        final AmbientAudioState state = widget.controller;
        final GtexTrackMetadata track = state.currentTrack;
        final bool isHyped = state.hypedTrackIds.contains(track.id);
        final int hypeTotal = state.hypeCountFor(track);
        final int tipTotal = state.artistTipTotals[track.id] ?? 0;
        final bool isAnthem = state.selectedGoalAnthemId == track.id;

        return DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.82,
          minChildSize: 0.45,
          maxChildSize: 0.94,
          builder: (BuildContext context, ScrollController scrollController) {
            return Container(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
              child: ListView(
                controller: scrollController,
                children: <Widget>[
                  Center(
                    child: Container(
                      width: 40,
                      height: 4,
                      margin: const EdgeInsets.only(bottom: 16),
                      decoration: BoxDecoration(
                        color: GtexColors.textMuted.withValues(alpha: 0.4),
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),

                  // Header Bar
                  Row(
                    children: <Widget>[
                      const Icon(Icons.graphic_eq_rounded, color: GtexColors.pitch, size: 28),
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            'GTEX SOUNDTRACK OS',
                            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              color: GtexColors.pitch,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 1.1,
                            ),
                          ),
                          Text(
                            'Audio & Atmosphere Settings',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              color: GtexColors.text,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ],
                      ),
                      const Spacer(),
                      IconButton(
                        tooltip: _showCredits ? 'Back to controls' : 'Music Credits',
                        icon: Icon(
                          _showCredits ? Icons.tune_rounded : Icons.info_outline_rounded,
                          color: GtexColors.textSecondary,
                        ),
                        onPressed: () {
                          setState(() {
                            _showCredits = !_showCredits;
                          });
                        },
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  if (state.isWebAutoplayBlocked) ...<Widget>[
                    Container(
                      padding: const EdgeInsets.all(12),
                      margin: const EdgeInsets.only(bottom: 16),
                      decoration: BoxDecoration(
                        color: GtexColors.gold.withValues(alpha: 0.15),
                        border: Border.all(color: GtexColors.gold.withValues(alpha: 0.5)),
                        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
                      ),
                      child: Row(
                        children: <Widget>[
                          const Icon(Icons.warning_amber_rounded, color: GtexColors.gold),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              'Browser blocked audio autoplay. Click below to enable sound.',
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: GtexColors.text,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          GtexButton(
                            label: 'Enable',
                            compact: true,
                            onPressed: () => state.resolveWebAutoplay(),
                          ),
                        ],
                      ),
                    ),
                  ],

                  if (_showCredits) ...<Widget>[
                    _buildCreditsView(context, state),
                  ] else ...<Widget>[
                    // Now Playing & Artist Spotlight Panel
                    GtexPanel(
                      title: track.title,
                      subtitle: '${track.artist} (${track.artistHandle}) • ${track.album}',
                      accent: track.isPromoted ? GtexColors.gold : GtexColors.pitch,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          const SizedBox(height: 6),
                          Wrap(
                            spacing: 8,
                            runSpacing: 4,
                            children: <Widget>[
                              if (track.isPromoted)
                                _Chip(
                                  label: '★ PROMOTED · ${track.sponsorTier.toUpperCase()}',
                                  color: GtexColors.gold,
                                ),
                              _Chip(label: track.genre, color: GtexColors.pitch),
                              _Chip(label: '${track.bpm} BPM', color: GtexColors.cyan),
                              _Chip(label: track.durationFormatted, color: GtexColors.gold),
                              _Chip(
                                label: 'Context: ${state.currentContext.label}',
                                color: GtexColors.mint,
                              ),
                              _Chip(label: track.region, color: GtexColors.cyan),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Text(
                            track.artistBio,
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: GtexColors.textSecondary,
                            ),
                          ),
                          const SizedBox(height: 12),

                          // Artist Promotion Engagement Actions: Hype, Tip Artist, Set Goal/Walkout Anthem
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: <Widget>[
                              InkWell(
                                onTap: () => state.toggleHypeTrack(track.id),
                                borderRadius: BorderRadius.circular(8),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                  decoration: BoxDecoration(
                                    color: isHyped
                                        ? GtexColors.gold.withValues(alpha: 0.22)
                                        : GtexColors.surfaceHover,
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(
                                      color: isHyped ? GtexColors.gold : GtexColors.surfaceBorder,
                                    ),
                                  ),
                                  child: Text(
                                    '🔥 HYPE ($hypeTotal)',
                                    style: TextStyle(
                                      color: isHyped ? GtexColors.gold : GtexColors.text,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                ),
                              ),
                              InkWell(
                                onTap: () => state.tipArtist(track.id, fanCoins: 10),
                                borderRadius: BorderRadius.circular(8),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                  decoration: BoxDecoration(
                                    color: GtexColors.pitch.withValues(alpha: 0.14),
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(color: GtexColors.pitch.withValues(alpha: 0.45)),
                                  ),
                                  child: Text(
                                    tipTotal > 0
                                        ? '💎 BACKED (+$tipTotal FAN)'
                                        : '💎 TIP ARTIST (+10 FAN)',
                                    style: const TextStyle(
                                      color: GtexColors.pitch,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                ),
                              ),
                              InkWell(
                                onTap: () => state.setGoalAnthemTrack(track.id),
                                borderRadius: BorderRadius.circular(8),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                  decoration: BoxDecoration(
                                    color: isAnthem
                                        ? GtexColors.cyan.withValues(alpha: 0.20)
                                        : GtexColors.surfaceHover,
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(
                                      color: isAnthem ? GtexColors.cyan : GtexColors.surfaceBorder,
                                    ),
                                  ),
                                  child: Text(
                                    isAnthem ? '⚽ ACTIVE GOAL/WALKOUT ANTHEM' : '⚽ SET AS GOAL ANTHEM',
                                    style: TextStyle(
                                      color: isAnthem ? GtexColors.cyan : GtexColors.textSecondary,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),

                          // External Artist Streaming Links
                          if (track.spotifyUrl != null ||
                              track.appleMusicUrl != null ||
                              track.audiomackUrl != null ||
                              track.youtubeUrl != null) ...<Widget>[
                            const SizedBox(height: 10),
                            Wrap(
                              spacing: 6,
                              runSpacing: 6,
                              children: <Widget>[
                                if (track.spotifyUrl != null)
                                  _StreamLinkButton(
                                    label: 'Spotify ↗',
                                    color: const Color(0xFF1DB954),
                                    onTap: () => _openExternalUrl(track.spotifyUrl),
                                  ),
                                if (track.appleMusicUrl != null)
                                  _StreamLinkButton(
                                    label: 'Apple Music ↗',
                                    color: const Color(0xFFFA243C),
                                    onTap: () => _openExternalUrl(track.appleMusicUrl),
                                  ),
                                if (track.audiomackUrl != null)
                                  _StreamLinkButton(
                                    label: 'Audiomack ↗',
                                    color: const Color(0xFFFFA200),
                                    onTap: () => _openExternalUrl(track.audiomackUrl),
                                  ),
                                if (track.youtubeUrl != null)
                                  _StreamLinkButton(
                                    label: 'YouTube ↗',
                                    color: const Color(0xFF38BDF8),
                                    onTap: () => _openExternalUrl(track.youtubeUrl),
                                  ),
                              ],
                            ),
                          ],

                          const SizedBox(height: 14),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: <Widget>[
                              IconButton(
                                key: const Key('audio-toggle-mute-sheet'),
                                tooltip: state.isMuted ? 'Unmute' : 'Mute',
                                icon: Icon(
                                  state.isMuted
                                      ? Icons.volume_off_rounded
                                      : Icons.volume_up_rounded,
                                  color: GtexColors.text,
                                ),
                                onPressed: () => state.toggleMuted(),
                              ),
                              const SizedBox(width: 12),
                              IconButton(
                                key: const Key('audio-play-pause-sheet'),
                                tooltip: state.isPlaying ? 'Pause' : 'Play',
                                iconSize: 40,
                                icon: Icon(
                                  state.isPlaying
                                      ? Icons.pause_circle_filled_rounded
                                      : Icons.play_circle_fill_rounded,
                                  color: GtexColors.pitch,
                                ),
                                onPressed: () {
                                  if (state.isPlaying) {
                                    state.pause();
                                  } else {
                                    state.play();
                                  }
                                },
                              ),
                              const SizedBox(width: 12),
                              IconButton(
                                key: const Key('audio-next-track-sheet'),
                                tooltip: 'Next Track',
                                icon: const Icon(Icons.skip_next_rounded, color: GtexColors.text),
                                onPressed: () => state.nextTrack(),
                              ),
                              IconButton(
                                key: const Key('audio-shuffle-sheet'),
                                tooltip: 'Shuffle Track',
                                icon: const Icon(Icons.shuffle_rounded, color: GtexColors.textSecondary),
                                onPressed: () => state.shuffleTrack(),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),

                    // Active Channel Mixer Sliders (Master & Music)
                    Text(
                      'ACTIVE AUDIO CHANNELS',
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: GtexColors.textMuted,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.9,
                      ),
                    ),
                    const SizedBox(height: 12),

                    // Master Volume
                    _VolumeSliderRow(
                      label: 'Master Volume',
                      icon: Icons.speaker_group_rounded,
                      value: state.masterVolume,
                      onChanged: (val) => state.setMasterVolume(val),
                      accent: GtexColors.pitch,
                    ),

                    // Music Volume
                    _VolumeSliderRow(
                      label: 'Music / Atmosphere',
                      icon: Icons.music_note_rounded,
                      value: state.musicVolume,
                      onChanged: (val) => state.setMusicVolume(val),
                      accent: GtexColors.cyan,
                    ),

                    const SizedBox(height: 20),

                    // Context Quick Switcher
                    Text(
                      'SOUNDTRACK CONTEXT',
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: GtexColors.textMuted,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.9,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: GtexAudioContext.values.map((ctx) {
                        final bool isActive = state.currentContext == ctx;
                        return ChoiceChip(
                          label: Text(ctx.label),
                          selected: isActive,
                          selectedColor: GtexColors.pitch,
                          backgroundColor: GtexColors.surfaceHover,
                          labelStyle: TextStyle(
                            color: isActive ? GtexColors.textInverse : GtexColors.text,
                            fontWeight: isActive ? FontWeight.w800 : FontWeight.w600,
                            fontSize: 12,
                          ),
                          onSelected: (_) {
                            state.setAudioContext(ctx);
                          },
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 20),

                    // Promoted Artist Roster / Jukebox Selector
                    Text(
                      'GTEX TRAX · PROMOTED ARTIST ROSTER',
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: GtexColors.gold,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.9,
                      ),
                    ),
                    const SizedBox(height: 10),
                    ...state.catalogue.allTracks.map((GtexTrackMetadata item) {
                      final bool selected = item.id == track.id;
                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: selected ? GtexColors.pitch : GtexColors.surfaceBorder,
                          ),
                        ),
                        child: Material(
                          color: selected
                              ? GtexColors.pitch.withValues(alpha: 0.12)
                              : GtexColors.surfaceHover,
                          borderRadius: BorderRadius.circular(10),
                          clipBehavior: Clip.antiAlias,
                          child: ListTile(
                          dense: true,
                          onTap: () => state.setTrack(item),
                          leading: Icon(
                            selected ? Icons.equalizer_rounded : Icons.album_rounded,
                            color: item.isPromoted ? GtexColors.gold : GtexColors.pitch,
                          ),
                          title: Text(
                            item.title,
                            style: TextStyle(
                              color: GtexColors.text,
                              fontWeight: FontWeight.w800,
                              fontSize: 13,
                            ),
                          ),
                          subtitle: Text(
                            '${item.artist} • ${item.genre} • ${item.region}',
                            style: const TextStyle(
                              color: GtexColors.textSecondary,
                              fontSize: 11,
                            ),
                          ),
                          trailing: _Chip(
                            label: item.isPromoted ? item.sponsorTier : 'Official',
                            color: item.isPromoted ? GtexColors.gold : GtexColors.pitch,
                          ),
                        ),
                      ),
                    );
                    }),
                  ],
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildCreditsView(BuildContext context, AmbientAudioState state) {
    final List<GtexTrackMetadata> catalogue = state.catalogue.allTracks;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'MUSIC CREDITS & LICENSING',
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: GtexColors.pitch,
            fontWeight: FontWeight.w900,
            letterSpacing: 1.0,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Every track bundled in GTEX has verified provenance and commercial licensing.',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: GtexColors.textSecondary,
          ),
        ),
        const SizedBox(height: 16),
        ...catalogue.map((track) => _TrackCreditCard(track: track)),
      ],
    );
  }
}

class _StreamLinkButton extends StatelessWidget {
  const _StreamLinkButton({
    required this.label,
    required this.color,
    required this.onTap,
  });

  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: color.withValues(alpha: 0.45)),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: 10,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

class _VolumeSliderRow extends StatelessWidget {
  const _VolumeSliderRow({
    required this.label,
    required this.icon,
    required this.value,
    required this.onChanged,
    required this.accent,
  });

  final String label;
  final IconData icon;
  final double value;
  final ValueChanged<double> onChanged;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final int percent = (value * 100).round();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: <Widget>[
          Icon(icon, color: accent, size: 20),
          const SizedBox(width: 12),
          SizedBox(
            width: 140,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: GtexColors.text,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Expanded(
            child: SliderTheme(
              data: SliderTheme.of(context).copyWith(
                activeTrackColor: accent,
                thumbColor: accent,
                overlayColor: accent.withValues(alpha: 0.2),
                trackHeight: 4,
              ),
              child: Slider(
                value: value,
                min: 0.0,
                max: 1.0,
                onChanged: onChanged,
              ),
            ),
          ),
          SizedBox(
            width: 42,
            child: Text(
              '$percent%',
              textAlign: TextAlign.right,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: GtexColors.textMuted,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TrackCreditCard extends StatelessWidget {
  const _TrackCreditCard({required this.track});

  final GtexTrackMetadata track;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: GtexColors.surfaceHover,
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: GtexColors.surfaceBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  track.title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              _Chip(label: track.genre, color: GtexColors.pitch),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            '${track.artist} • ${track.album}',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: GtexColors.textSecondary,
            ),
          ),
          const SizedBox(height: 8),
          _CreditInfoRow(label: 'Licence:', value: track.licence),
          _CreditInfoRow(label: 'Source:', value: track.source),
          _CreditInfoRow(label: 'Provenance:', value: track.provenance),
          const SizedBox(height: 6),
          InkWell(
            onTap: () async {
              final Uri uri = Uri.parse(track.licenceUrl);
              if (await canLaunchUrl(uri)) {
                await launchUrl(uri);
              }
            },
            child: Text(
              'Licence Terms & Verification →',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: GtexColors.cyan,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CreditInfoRow extends StatelessWidget {
  const _CreditInfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            width: 80,
            child: Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: GtexColors.textMuted,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: GtexColors.text,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        border: Border.all(color: color.withValues(alpha: 0.4)),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}
