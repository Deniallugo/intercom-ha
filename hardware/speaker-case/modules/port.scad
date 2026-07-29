// ===== tuned port tube (no top-level geometry) =====
// A separate printed part on purpose: Fb is empirical, and reprinting a 5 g tube is
// far cheaper than reprinting the box. Slide-fits the +x side-wall bore, flange
// registered flush in the outer face.
//
//   Lv = 23562.5 * d^2 / (Fb^2 * Vb) - 0.732 * d      (d in cm, Vb in litres)
//
// At Vb = 0.705 L and d = 2.0 cm:
//   port_len 40 mm -> Fb ~156 Hz
//   port_len 49 mm -> Fb ~145 Hz   (default: tuned AT Fs)
//   port_len 60 mm -> Fb ~134 Hz
//   port_len 75 mm -> Fb ~122 Hz
// Do not chase lower. Below Fs the cones cannot drive the port, and the box unloads —
// that is exactly the mistake the 75 Hz passive radiator made.
//
// Both ends get a small radius: a flared port chuffs at a higher velocity than a
// straight-cut one, and printing makes the flare free.

port_fillet = 2;

module port_tube() {
    difference() {
        union() {
            // flange (sits in the outer-face register)
            cylinder(h = port_flange_t, d = port_flange_od);
            // barrel: full acoustic length measured from the outer face
            cylinder(h = port_len, d = port_od());
        }
        // bore, with a radiused mouth at each end
        translate([0, 0, -0.1]) cylinder(h = port_len + 0.2, d = port_id);
        translate([0, 0, -0.01])
            cylinder(h = port_fillet, d1 = port_id + 2*port_fillet, d2 = port_id);
        translate([0, 0, port_len - port_fillet + 0.01])
            cylinder(h = port_fillet, d1 = port_id, d2 = port_id + 2*port_fillet);
    }
}
