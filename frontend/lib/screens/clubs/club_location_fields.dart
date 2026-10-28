import 'package:flutter/material.dart';

import '../../ui_gtex/theme/gtex_colors.dart';
import '../../ui_gtex/theme/gtex_spacing.dart';

/// Selectable club home locations.
///
/// Values follow the existing `POST /api/clubs` contract: `country_code` is an
/// upper-case ISO 3166-1 alpha-2 code and `region_name` / `city_name` are
/// trimmed display names. The catalog drives search and autofill only; a city
/// or region that is not listed can still be typed. The data mirrors
/// `frontend/react-shell/src/pages/clubLocationCatalog.ts`.
class ClubLocationCity {
  const ClubLocationCity(this.city, this.region);
  final String city;
  final String region;
}

class ClubLocationCountry {
  const ClubLocationCountry(this.code, this.name, this.cities);
  final String code;
  final String name;
  final List<ClubLocationCity> cities;

  String get label => '$name ($code)';
}

const List<ClubLocationCountry> kClubLocationCatalog = <ClubLocationCountry>[
  ClubLocationCountry('AR', 'Argentina', <ClubLocationCity>[
    ClubLocationCity('Buenos Aires', 'Buenos Aires'),
    ClubLocationCity('Córdoba', 'Córdoba'),
    ClubLocationCity('Rosario', 'Santa Fe'),
  ]),
  ClubLocationCountry('AU', 'Australia', <ClubLocationCity>[
    ClubLocationCity('Sydney', 'New South Wales'),
    ClubLocationCity('Melbourne', 'Victoria'),
    ClubLocationCity('Brisbane', 'Queensland'),
  ]),
  ClubLocationCountry('BR', 'Brazil', <ClubLocationCity>[
    ClubLocationCity('São Paulo', 'São Paulo'),
    ClubLocationCity('Rio de Janeiro', 'Rio de Janeiro'),
    ClubLocationCity('Salvador', 'Bahia'),
  ]),
  ClubLocationCountry('CA', 'Canada', <ClubLocationCity>[
    ClubLocationCity('Toronto', 'Ontario'),
    ClubLocationCity('Vancouver', 'British Columbia'),
    ClubLocationCity('Montreal', 'Quebec'),
  ]),
  ClubLocationCountry('CM', 'Cameroon', <ClubLocationCity>[
    ClubLocationCity('Douala', 'Littoral'),
    ClubLocationCity('Yaoundé', 'Centre'),
  ]),
  ClubLocationCountry('CI', "Côte d'Ivoire", <ClubLocationCity>[
    ClubLocationCity('Abidjan', 'Lagunes'),
    ClubLocationCity('Bouaké', 'Vallée du Bandama'),
  ]),
  ClubLocationCountry('DE', 'Germany', <ClubLocationCity>[
    ClubLocationCity('Berlin', 'Berlin'),
    ClubLocationCity('Munich', 'Bavaria'),
    ClubLocationCity('Hamburg', 'Hamburg'),
  ]),
  ClubLocationCountry('EG', 'Egypt', <ClubLocationCity>[
    ClubLocationCity('Cairo', 'Cairo'),
    ClubLocationCity('Alexandria', 'Alexandria'),
  ]),
  ClubLocationCountry('ES', 'Spain', <ClubLocationCity>[
    ClubLocationCity('Madrid', 'Community of Madrid'),
    ClubLocationCity('Barcelona', 'Catalonia'),
    ClubLocationCity('Seville', 'Andalusia'),
  ]),
  ClubLocationCountry('FR', 'France', <ClubLocationCity>[
    ClubLocationCity('Paris', 'Île-de-France'),
    ClubLocationCity('Marseille', "Provence-Alpes-Côte d'Azur"),
    ClubLocationCity('Lyon', 'Auvergne-Rhône-Alpes'),
  ]),
  ClubLocationCountry('GB', 'United Kingdom', <ClubLocationCity>[
    ClubLocationCity('London', 'England'),
    ClubLocationCity('Manchester', 'England'),
    ClubLocationCity('Glasgow', 'Scotland'),
    ClubLocationCity('Cardiff', 'Wales'),
  ]),
  ClubLocationCountry('GH', 'Ghana', <ClubLocationCity>[
    ClubLocationCity('Accra', 'Greater Accra'),
    ClubLocationCity('Kumasi', 'Ashanti'),
  ]),
  ClubLocationCountry('IN', 'India', <ClubLocationCity>[
    ClubLocationCity('Mumbai', 'Maharashtra'),
    ClubLocationCity('Delhi', 'Delhi'),
    ClubLocationCity('Kolkata', 'West Bengal'),
  ]),
  ClubLocationCountry('IT', 'Italy', <ClubLocationCity>[
    ClubLocationCity('Rome', 'Lazio'),
    ClubLocationCity('Milan', 'Lombardy'),
    ClubLocationCity('Naples', 'Campania'),
  ]),
  ClubLocationCountry('JP', 'Japan', <ClubLocationCity>[
    ClubLocationCity('Tokyo', 'Tokyo'),
    ClubLocationCity('Osaka', 'Osaka'),
    ClubLocationCity('Yokohama', 'Kanagawa'),
  ]),
  ClubLocationCountry('KE', 'Kenya', <ClubLocationCity>[
    ClubLocationCity('Nairobi', 'Nairobi'),
    ClubLocationCity('Mombasa', 'Mombasa'),
  ]),
  ClubLocationCountry('MA', 'Morocco', <ClubLocationCity>[
    ClubLocationCity('Casablanca', 'Casablanca-Settat'),
    ClubLocationCity('Rabat', 'Rabat-Salé-Kénitra'),
  ]),
  ClubLocationCountry('MX', 'Mexico', <ClubLocationCity>[
    ClubLocationCity('Mexico City', 'Mexico City'),
    ClubLocationCity('Guadalajara', 'Jalisco'),
    ClubLocationCity('Monterrey', 'Nuevo León'),
  ]),
  ClubLocationCountry('NG', 'Nigeria', <ClubLocationCity>[
    ClubLocationCity('Lagos', 'Lagos'),
    ClubLocationCity('Abuja', 'FCT'),
    ClubLocationCity('Port Harcourt', 'Rivers'),
    ClubLocationCity('Kano', 'Kano'),
  ]),
  ClubLocationCountry('NL', 'Netherlands', <ClubLocationCity>[
    ClubLocationCity('Amsterdam', 'North Holland'),
    ClubLocationCity('Rotterdam', 'South Holland'),
  ]),
  ClubLocationCountry('PT', 'Portugal', <ClubLocationCity>[
    ClubLocationCity('Lisbon', 'Lisbon'),
    ClubLocationCity('Porto', 'Porto'),
  ]),
  ClubLocationCountry('SA', 'Saudi Arabia', <ClubLocationCity>[
    ClubLocationCity('Riyadh', 'Riyadh'),
    ClubLocationCity('Jeddah', 'Makkah'),
  ]),
  ClubLocationCountry('SN', 'Senegal', <ClubLocationCity>[
    ClubLocationCity('Dakar', 'Dakar'),
    ClubLocationCity('Thiès', 'Thiès'),
  ]),
  ClubLocationCountry('US', 'United States', <ClubLocationCity>[
    ClubLocationCity('New York', 'New York'),
    ClubLocationCity('Los Angeles', 'California'),
    ClubLocationCity('Chicago', 'Illinois'),
    ClubLocationCity('Houston', 'Texas'),
  ]),
  ClubLocationCountry('ZA', 'South Africa', <ClubLocationCity>[
    ClubLocationCity('Johannesburg', 'Gauteng'),
    ClubLocationCity('Cape Town', 'Western Cape'),
    ClubLocationCity('Durban', 'KwaZulu-Natal'),
  ]),
];

String _fold(String value) {
  const String from = 'àáâãäåçèéêëìíîïñòóôõöùúûüýÿ';
  const String to = 'aaaaaaceeeeiiiinooooouuuuyy';
  final StringBuffer out = StringBuffer();
  for (final int rune in value.trim().toLowerCase().runes) {
    final String ch = String.fromCharCode(rune);
    final int i = from.indexOf(ch);
    out.write(i >= 0 ? to[i] : ch);
  }
  return out.toString();
}

/// Resolve a label ("Ghana (GH)"), a name or a bare alpha-2 code to a country.
ClubLocationCountry? resolveClubCountry(String input) {
  final String text = _fold(input);
  if (text.isEmpty) {
    return null;
  }
  for (final ClubLocationCountry country in kClubLocationCatalog) {
    if (_fold(country.label) == text ||
        _fold(country.name) == text ||
        country.code.toLowerCase() == text) {
      return country;
    }
  }
  return null;
}

ClubLocationCity? _findCity(ClubLocationCountry? country, String input) {
  if (country == null) {
    return null;
  }
  final String text = _fold(input);
  for (final ClubLocationCity city in country.cities) {
    if (_fold(city.city) == text) {
      return city;
    }
  }
  return null;
}

/// Normalized values ready for `GteCreateClubRequest`.
class ClubLocationSelection {
  const ClubLocationSelection({
    required this.countryCode,
    required this.regionName,
    required this.cityName,
  });

  final String countryCode;
  final String regionName;
  final String cityName;
}

/// Holds the country / region / city inputs. Starts empty: there is no default
/// country, region or city.
class ClubLocationController extends ChangeNotifier {
  final TextEditingController region = TextEditingController();
  ClubLocationCountry? _country;
  String _countryText = '';
  String _city = '';
  bool _regionEdited = false;

  ClubLocationCountry? get country => _country;
  String get countryText => _countryText;
  String get city => _city;

  void setCountryText(String text) {
    final ClubLocationCountry? next = resolveClubCountry(text);
    final bool changed = next?.code != _country?.code;
    _countryText = text;
    _country = next;
    if (changed) {
      _city = '';
      region.clear();
      _regionEdited = false;
    }
    notifyListeners();
  }

  void setCity(String text) {
    _city = text;
    final ClubLocationCity? known = _findCity(_country, text);
    if (known != null && !_regionEdited) {
      region.text = known.region;
    }
    notifyListeners();
  }

  void setRegionEdited() {
    _regionEdited = true;
  }

  /// Returns an error message, or null when the location is valid.
  String? validate() {
    if (_country == null) {
      return "Select the club's country.";
    }
    if (_city.trim().length < 2) {
      return 'Enter the club home city.';
    }
    if (region.text.trim().length < 2) {
      return "Enter the club's region or state.";
    }
    if (_city.trim().length > 120 || region.text.trim().length > 120) {
      return 'City and region must be 120 characters or fewer.';
    }
    return null;
  }

  ClubLocationSelection? get selection {
    if (validate() != null) {
      return null;
    }
    final String cityInput = _city.trim().replaceAll(RegExp(r'\s+'), ' ');
    return ClubLocationSelection(
      countryCode: _country!.code,
      regionName: region.text.trim().replaceAll(RegExp(r'\s+'), ' '),
      cityName: _findCity(_country, cityInput)?.city ?? cityInput,
    );
  }

  @override
  void dispose() {
    region.dispose();
    super.dispose();
  }
}

typedef ClubLocationDecoration = InputDecoration Function({
  required String label,
  required IconData icon,
  String? hint,
});

/// Searchable country / city inputs plus a region field. Fields stack on
/// narrow widths and sit in a row on wide ones.
class ClubLocationFields extends StatelessWidget {
  const ClubLocationFields({
    super.key,
    required this.controller,
    required this.decoration,
    this.errorText,
  });

  final ClubLocationController controller;
  final ClubLocationDecoration decoration;
  final String? errorText;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controller,
      builder: (BuildContext context, Widget? _) {
        final ClubLocationCountry? country = controller.country;
        final Widget countryField = _SearchField<ClubLocationCountry>(
          fieldKey: const ValueKey<String>('club-location-country'),
          label: 'Country',
          hint: 'Search country',
          icon: Icons.flag_outlined,
          decoration: decoration,
          options: kClubLocationCatalog,
          optionLabel: (ClubLocationCountry c) => c.label,
          matches: (ClubLocationCountry c, String q) =>
              _fold(c.name).contains(q) || c.code.toLowerCase() == q,
          onChanged: controller.setCountryText,
        );
        final Widget cityField = _SearchField<ClubLocationCity>(
          // Rebuild (and clear) the city box when the country changes.
          fieldKey: ValueKey<String>('club-location-city-${country?.code}'),
          label: 'City',
          hint: country == null ? 'Select a country first' : 'Search city',
          icon: Icons.location_city_outlined,
          decoration: decoration,
          enabled: country != null,
          options: country?.cities ?? const <ClubLocationCity>[],
          optionLabel: (ClubLocationCity c) => c.city,
          matches: (ClubLocationCity c, String q) => _fold(c.city).contains(q),
          onChanged: controller.setCity,
        );
        final Widget regionField = TextField(
          key: const ValueKey<String>('club-location-region'),
          controller: controller.region,
          enabled: country != null,
          style: const TextStyle(color: GtexColors.text),
          decoration: decoration(
            label: 'Region / state',
            icon: Icons.map_outlined,
          ),
          onChanged: (_) => controller.setRegionEdited(),
        );
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                if (constraints.maxWidth >= 720) {
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Expanded(child: countryField),
                      const SizedBox(width: GtexSpacing.sm),
                      Expanded(child: cityField),
                      const SizedBox(width: GtexSpacing.sm),
                      Expanded(child: regionField),
                    ],
                  );
                }
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    countryField,
                    const SizedBox(height: GtexSpacing.sm),
                    cityField,
                    const SizedBox(height: GtexSpacing.sm),
                    regionField,
                  ],
                );
              },
            ),
            if (errorText != null) ...<Widget>[
              const SizedBox(height: GtexSpacing.xs),
              Text(
                errorText!,
                key: const ValueKey<String>('club-location-error'),
                style: const TextStyle(color: GtexColors.danger),
              ),
            ],
          ],
        );
      },
    );
  }
}

class _SearchField<T extends Object> extends StatelessWidget {
  const _SearchField({
    required this.fieldKey,
    required this.label,
    required this.hint,
    required this.icon,
    required this.decoration,
    required this.options,
    required this.optionLabel,
    required this.matches,
    required this.onChanged,
    this.enabled = true,
  });

  final Key fieldKey;
  final String label;
  final String hint;
  final IconData icon;
  final ClubLocationDecoration decoration;
  final List<T> options;
  final String Function(T) optionLabel;
  final bool Function(T, String) matches;
  final ValueChanged<String> onChanged;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Autocomplete<T>(
      key: fieldKey,
      displayStringForOption: optionLabel,
      optionsBuilder: (TextEditingValue value) {
        final String query = _fold(value.text);
        if (!enabled) {
          return Iterable<T>.empty();
        }
        return options.where((T o) => query.isEmpty || matches(o, query));
      },
      onSelected: (T option) => onChanged(optionLabel(option)),
      fieldViewBuilder: (
        BuildContext context,
        TextEditingController textController,
        FocusNode focusNode,
        VoidCallback onFieldSubmitted,
      ) {
        return TextField(
          controller: textController,
          focusNode: focusNode,
          enabled: enabled,
          style: const TextStyle(color: GtexColors.text),
          decoration: decoration(label: label, icon: icon, hint: hint),
          onChanged: onChanged,
          onSubmitted: (_) => onFieldSubmitted(),
        );
      },
    );
  }
}
