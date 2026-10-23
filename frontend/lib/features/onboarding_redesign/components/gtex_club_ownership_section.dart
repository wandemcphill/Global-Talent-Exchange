import 'package:flutter/material.dart';

import 'gtex_home_models.dart';
import 'gtex_home_shared_widgets.dart';

class GtexClubOwnershipSection extends StatefulWidget {
  const GtexClubOwnershipSection({
    super.key,
    this.onClaimClub,
  });

  final VoidCallback? onClaimClub;

  @override
  State<GtexClubOwnershipSection> createState() => _GtexClubOwnershipSectionState();
}

class _GtexClubOwnershipSectionState extends State<GtexClubOwnershipSection> {
  int _selectedStageIndex = 4; // Start on Legacy stage to showcase the ultimate destination
  int _selectedAssetIndex = 0; // Sovereign 900X Jet

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.sizeOf(context).width;
    final bool isNarrow = width < 760;
    final ClubStageData currentStage = kClubStages[_selectedStageIndex];
    final ShowroomAssetItem currentAsset = kShowroomAssets[_selectedAssetIndex];

    return Container(
      color: kNavyBase,
      padding: EdgeInsets.symmetric(
        horizontal: isNarrow ? 20 : 64,
        vertical: 64,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          // Section Masthead
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Expanded(
                child: GtexSectionHeader(
                  eyebrow: 'Club Ownership & Simulation Life',
                  title: 'From Grassroots Founder to Global Football Institution',
                  subtitle: 'Every owner can found or acquire up to three clubs. Define club identity, construct world-class facilities, appoint tacticians, and unlock luxury aviation as your institutional prestige rises.',
                  accentColor: kGoldPrimary,
                ),
              ),
              if (!isNarrow) ...<Widget>[
                const SizedBox(width: 24),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                  decoration: BoxDecoration(
                    color: kNavyRaised,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: kGoldPrimary.withValues(alpha: 0.4)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const <Widget>[
                      Text(
                        'PORTFOLIO LIMIT',
                        style: TextStyle(
                          color: kGoldPrimary,
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 1.2,
                          fontFamily: kFontCondensed,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'Up to 3 Active Clubs',
                        style: TextStyle(
                          color: kTextPrimary,
                          fontSize: 15,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      Text(
                        'Independent sporting ledgers',
                        style: TextStyle(
                          color: kTextTertiary,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),

          const SizedBox(height: 36),

          // Interactive Stage Selector Tabs
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: List<Widget>.generate(kClubStages.length, (int index) {
                final ClubStageData stage = kClubStages[index];
                final bool isSelected = index == _selectedStageIndex;
                return Padding(
                  padding: const EdgeInsets.only(right: 12),
                  child: InkWell(
                    onTap: () => setState(() => _selectedStageIndex = index),
                    borderRadius: BorderRadius.circular(12),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      decoration: BoxDecoration(
                        color: isSelected ? kNavyOverlay : kNavyRaised,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: isSelected ? stage.badgeColor : kNavyLine,
                          width: isSelected ? 2 : 1,
                        ),
                        boxShadow: isSelected
                            ? <BoxShadow>[
                                BoxShadow(
                                  color: stage.badgeColor.withValues(alpha: 0.25),
                                  blurRadius: 12,
                                  offset: const Offset(0, 4),
                                ),
                              ]
                            : null,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            'STAGE ${index + 1}',
                            style: TextStyle(
                              color: isSelected ? stage.badgeColor : kTextTertiary,
                              fontSize: 10,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 1.2,
                              fontFamily: kFontCondensed,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            stage.name,
                            style: TextStyle(
                              color: isSelected ? kTextPrimary : kTextSecondary,
                              fontSize: 13,
                              fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'TV Share: ${stage.tvSharePercentage}%',
                            style: const TextStyle(
                              color: kPitchGreenBright,
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              fontFamily: kFontMono,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }),
            ),
          ),

          const SizedBox(height: 20),

          // Stage Detail Showcase Card
          Container(
            decoration: BoxDecoration(
              color: kNavyRaised,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: currentStage.badgeColor.withValues(alpha: 0.5)),
            ),
            padding: EdgeInsets.all(isNarrow ? 18 : 28),
            child: LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool wide = constraints.maxWidth > 700;
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Wrap(
                      spacing: 12,
                      runSpacing: 6,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: <Widget>[
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: currentStage.badgeColor.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: currentStage.badgeColor),
                          ),
                          child: Text(
                            currentStage.scoreRange.toUpperCase(),
                            style: TextStyle(
                              color: currentStage.badgeColor,
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                              fontFamily: kFontCondensed,
                              letterSpacing: 1,
                            ),
                          ),
                        ),
                        Text(
                          currentStage.name,
                          style: const TextStyle(
                            color: kTextPrimary,
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                            fontFamily: kFontCondensed,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    if (wide)
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Expanded(child: _StageFeatureBlock(title: 'FACILITIES & STADIUM', value: currentStage.facilitiesTitle, description: currentStage.facilitiesDescription, icon: Icons.stadium_rounded)),
                          const SizedBox(width: 16),
                          Expanded(child: _StageFeatureBlock(title: 'TELEVISION DISTRIBUTION', value: '${currentStage.tvSharePercentage}% Club TV Share', description: 'Host club retains 40% of club tournament pool; remainder split among participants.', icon: Icons.tv_rounded, accentColor: kPitchGreenBright)),
                          const SizedBox(width: 16),
                          Expanded(child: _StageFeatureBlock(title: 'FLEET & LUXURY UNLOCK', value: currentStage.luxuryAssetAvailable, description: 'Institutional assets boost owner prestige and accelerate matchday travel.', icon: Icons.flight_takeoff_rounded, accentColor: kGoldPrimary)),
                        ],
                      )
                    else
                      Column(
                        children: <Widget>[
                          _StageFeatureBlock(title: 'FACILITIES & STADIUM', value: currentStage.facilitiesTitle, description: currentStage.facilitiesDescription, icon: Icons.stadium_rounded),
                          const SizedBox(height: 14),
                          _StageFeatureBlock(title: 'TELEVISION DISTRIBUTION', value: '${currentStage.tvSharePercentage}% Club TV Share', description: 'Host club retains 40% of club tournament pool; remainder split among participants.', icon: Icons.tv_rounded, accentColor: kPitchGreenBright),
                          const SizedBox(height: 14),
                          _StageFeatureBlock(title: 'FLEET & LUXURY UNLOCK', value: currentStage.luxuryAssetAvailable, description: 'Institutional assets boost owner prestige and accelerate matchday travel.', icon: Icons.flight_takeoff_rounded, accentColor: kGoldPrimary),
                        ],
                      ),
                  ],
                );
              },
            ),
          ),

          const SizedBox(height: 40),

          // Luxury Showroom Sub-Section
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 10,
            runSpacing: 6,
            children: <Widget>[
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 8,
                children: const <Widget>[
                  Icon(Icons.diamond_rounded, color: kGoldPrimary, size: 20),
                  Text(
                    'THE OWNER LUXURY SHOWROOM',
                    style: TextStyle(
                      color: kGoldPrimary,
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.5,
                      fontFamily: kFontCondensed,
                    ),
                  ),
                ],
              ),
              const Text(
                'LUXURY FLEET • STADIUMS • FACILITIES',
                style: TextStyle(
                  color: kTextTertiary,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1,
                  fontFamily: kFontCondensed,
                ),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Luxury Asset Selector & Showcase Card
          Container(
            decoration: BoxDecoration(
              color: kNavyInset,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: kNavyLineStrong),
            ),
            padding: EdgeInsets.all(isNarrow ? 16 : 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                // Asset thumbnail tabs
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: List<Widget>.generate(kShowroomAssets.length, (int index) {
                      final ShowroomAssetItem asset = kShowroomAssets[index];
                      final bool isSelected = index == _selectedAssetIndex;
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ChoiceChip(
                          label: Text(asset.name),
                          selected: isSelected,
                          onSelected: (_) => setState(() => _selectedAssetIndex = index),
                          selectedColor: kGoldPrimary.withValues(alpha: 0.2),
                          backgroundColor: kNavyRaised,
                          labelStyle: TextStyle(
                            color: isSelected ? kGoldLight : kTextSecondary,
                            fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                            fontSize: 12,
                          ),
                          side: BorderSide(
                            color: isSelected ? kGoldPrimary : kNavyLine,
                          ),
                        ),
                      );
                    }),
                  ),
                ),

                const SizedBox(height: 20),

                // Featured Asset Layout
                LayoutBuilder(
                  builder: (BuildContext context, BoxConstraints constraints) {
                    final bool isWide = constraints.maxWidth > 720;
                    return isWide
                        ? Row(
                            crossAxisAlignment: CrossAxisAlignment.center,
                            children: <Widget>[
                              Expanded(
                                flex: 5,
                                child: _AssetImageFrame(imageFile: currentAsset.imageFile),
                              ),
                              const SizedBox(width: 28),
                              Expanded(
                                flex: 6,
                                child: _AssetDetailView(asset: currentAsset),
                              ),
                            ],
                          )
                        : Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              _AssetImageFrame(imageFile: currentAsset.imageFile),
                              const SizedBox(height: 18),
                              _AssetDetailView(asset: currentAsset),
                            ],
                          );
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StageFeatureBlock extends StatelessWidget {
  const _StageFeatureBlock({
    required this.title,
    required this.value,
    required this.description,
    required this.icon,
    this.accentColor = kSkyBlue,
  });

  final String title;
  final String value;
  final String description;
  final IconData icon;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: kNavyInset,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: kNavyLine),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(icon, size: 16, color: accentColor),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    color: accentColor,
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1,
                    fontFamily: kFontCondensed,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: const TextStyle(
              color: kTextPrimary,
              fontSize: 14,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            description,
            style: const TextStyle(
              color: kTextSecondary,
              fontSize: 12,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}

class _AssetImageFrame extends StatelessWidget {
  const _AssetImageFrame({required this.imageFile});

  final String imageFile;

  @override
  Widget build(BuildContext context) {
    final bool isJet = imageFile.endsWith('sovereign_900x_jet.png');
    final bool isNarrow = MediaQuery.sizeOf(context).width < 760;

    return Container(
      height: isNarrow ? 240 : 360,
      decoration: BoxDecoration(
        color: kNavyRaised,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isJet
              ? kGoldPrimary.withValues(alpha: 0.68)
              : kNavyLineStrong,
        ),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Color(0xFF15243A),
            Color(0xFF080F1B),
            Color(0xFF101B2D),
          ],
        ),
        boxShadow: isJet
            ? <BoxShadow>[
                BoxShadow(
                  color: kGoldPrimary.withValues(alpha: 0.10),
                  blurRadius: 24,
                  spreadRadius: 1,
                ),
              ]
            : const <BoxShadow>[],
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          if (isJet)
            const DecoratedBox(
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: Alignment(0.05, -0.15),
                  radius: 0.82,
                  colors: <Color>[
                    Color(0x2BDFB63E),
                    Color(0x0D4EA1C8),
                    Colors.transparent,
                  ],
                  stops: <double>[0, 0.46, 1],
                ),
              ),
            ),
          Image.asset(
            imageFile,
            fit: BoxFit.contain,
            alignment: Alignment.center,
            errorBuilder: (_, __, ___) => Icon(
              isJet ? Icons.flight_takeoff_rounded : Icons.image_not_supported_outlined,
              size: 64,
              color: isJet ? kGoldPrimary : kTextTertiary,
            ),
          ),
          if (isJet)
            Positioned(
              left: 12,
              bottom: 12,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0xD9081120),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: kGoldPrimary.withValues(alpha: 0.55),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    const Icon(
                      Icons.flight_takeoff_rounded,
                      size: 13,
                      color: kGoldLight,
                    ),
                    const SizedBox(width: 7),
                    const Text(
                      'GTEX AVIATION  /  OWNER ASSET',
                      style: TextStyle(
                        color: kGoldLight,
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1,
                        fontFamily: kFontCondensed,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _AssetDetailView extends StatelessWidget {
  const _AssetDetailView({required this.asset});

  final ShowroomAssetItem asset;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Wrap(
          spacing: 8,
          runSpacing: 6,
          children: <Widget>[
            GtexTagPill(label: asset.category, color: kSkyBlue),
            GtexTagPill(label: asset.tag, color: kGoldPrimary),
          ],
        ),
        const SizedBox(height: 10),
        Text(
          asset.name,
          style: const TextStyle(
            color: kTextPrimary,
            fontSize: 24,
            fontWeight: FontWeight.w900,
            fontFamily: kFontCondensed,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          asset.model,
          style: const TextStyle(
            color: kGoldLight,
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 10),
        Text(
          asset.description,
          style: const TextStyle(
            color: kTextSecondary,
            fontSize: 13,
            height: 1.45,
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: kNavyRaised,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: kNavyLine),
          ),
          child: Wrap(
            alignment: WrapAlignment.spaceAround,
            spacing: 12,
            runSpacing: 8,
            children: <Widget>[
              _AssetStat(label: 'PRICE', value: '${asset.priceGtex.toStringAsFixed(0)} GTX'),
              _AssetStat(label: 'PRESTIGE', value: '+${asset.prestigeBonus} PTS'),
              _AssetStat(label: 'GIFTING', value: asset.canGiftToPlayer ? 'ELIGIBLE' : 'CLUB ONLY'),
            ],
          ),
        ),
      ],
    );
  }
}

class _AssetStat extends StatelessWidget {
  const _AssetStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text(
          label,
          style: const TextStyle(
            color: kTextTertiary,
            fontSize: 10,
            fontWeight: FontWeight.w700,
            letterSpacing: 1,
            fontFamily: kFontCondensed,
          ),
        ),
        const SizedBox(height: 3),
        Text(
          value,
          style: const TextStyle(
            color: kGoldLight,
            fontSize: 13,
            fontWeight: FontWeight.w800,
            fontFamily: kFontMono,
          ),
        ),
      ],
    );
  }
}
