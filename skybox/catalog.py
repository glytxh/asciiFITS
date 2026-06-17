CATALOG_GROUPS = [
    (
        "Galaxies",
        [
            ("M31", "Andromeda Galaxy", "Large nearby spiral; excellent survey-scale target."),
            ("M33", "Triangulum Galaxy", "Diffuse nearby spiral; good for atlas/survey views."),
            ("M51", "Whirlpool Galaxy", "Face-on interacting spiral; strong morphology."),
            ("M81", "Bode's Galaxy", "Bright spiral; clean structure."),
            ("M82", "Cigar Galaxy", "Edge-on starburst galaxy; high-contrast shape."),
            ("M87", "Virgo A", "Giant elliptical; useful as a different galaxy profile."),
            ("M101", "Pinwheel Galaxy", "Large face-on spiral; very good atlas target."),
            ("NGC 253", "Sculptor Galaxy", "Bright inclined starburst galaxy."),
            ("NGC 4565", "Needle Galaxy", "Classic edge-on spiral."),
        ],
    ),
    (
        "Nebulae",
        [
            ("M42", "Orion Nebula", "Bright emission nebula; strong structure."),
            ("M8", "Lagoon Nebula", "Large emission nebula; good wide-field target."),
            ("M16", "Eagle Nebula", "Emission nebula and cluster field."),
            ("M17", "Omega Nebula", "Bright nebular structure."),
            ("M27", "Dumbbell Nebula", "Large planetary nebula."),
            ("M57", "Ring Nebula", "Compact planetary nebula."),
            ("NGC 7000", "North America Nebula", "Huge diffuse nebula; needs wide/survey scale."),
        ],
    ),
    (
        "Clusters",
        [
            ("M13", "Hercules Globular Cluster", "Dense globular cluster; good texture test."),
            ("M15", "Pegasus Globular Cluster", "Compact bright globular."),
            ("M44", "Beehive Cluster", "Large open cluster; benefits from wider fields."),
            ("M45", "Pleiades", "Large bright open cluster."),
            ("NGC 869", "Double Cluster h Persei", "Rich open cluster field."),
            ("NGC 884", "Double Cluster chi Persei", "Companion rich open cluster field."),
        ],
    ),
    (
        "Deep / odd",
        [
            ("3C 273", "Bright quasar", "Historically important quasar; point-like but grounded."),
            ("Cygnus A", "Radio galaxy", "Powerful radio galaxy; optical counterpart challenge."),
            ("NGC 1275", "Perseus A", "Active galaxy in Perseus cluster."),
            ("Arp 220", "Ultraluminous infrared galaxy", "Merger remnant; faint but interesting."),
        ],
    ),
]


def catalog_entries():
    entries = []

    for group_name, group_entries in CATALOG_GROUPS:
        for object_name, common_name, note in group_entries:
            entries.append(
                {
                    "group": group_name,
                    "object": object_name,
                    "name": common_name,
                    "note": note,
                }
            )

    return entries
