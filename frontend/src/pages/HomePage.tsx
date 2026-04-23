export function HomePage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "2rem",
        background:
          "linear-gradient(135deg, #f8f4e8 0%, #d9efe7 55%, #b7d3d8 100%)",
        color: "#162521",
        fontFamily: 'Georgia, "Times New Roman", serif',
      }}
    >
      <section style={{ maxWidth: 760 }}>
        <p
          style={{
            margin: 0,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
          }}
        >
          Research-Flow
        </p>
        <h1
          style={{
            margin: "0.4rem 0 1rem",
            fontSize: "clamp(2.6rem, 8vw, 5.8rem)",
          }}
        >
          Full-cycle research workspace
        </h1>
        <p
          style={{
            margin: 0,
            maxWidth: 620,
            fontSize: "1.2rem",
            lineHeight: 1.7,
          }}
        >
          A minimal shell is ready. Literature intake, paper parsing, project
          tracking, and writing workflows can now be mounted as product routes.
        </p>
      </section>
    </main>
  );
}
