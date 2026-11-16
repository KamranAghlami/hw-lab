# CI image: pinned KiCad + KiBot toolchain, pushed to GHCR by .github/workflows/ci-image.yml.
# KiCad version must match the owner's desktop (see docs/memory/owner-decisions.md).
FROM kicad/kicad:10.0.8
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3-venv python3-pip git zip imagemagick librsvg2-bin poppler-utils ghostscript \
      openjdk-21-jre-headless curl \
 && rm -rf /var/lib/apt/lists/*
# venv sees the system pcbnew module (--system-site-packages); never pip into system python
RUN python3 -m venv --system-site-packages /opt/kibot \
 && /opt/kibot/bin/pip install --no-cache-dir --no-compile \
      kibot==1.9.1 kiauto InteractiveHtmlBom==2.12.0 kidiff==2.6.0 \
      lxml numpy svgwrite mistune
# Freerouting for the optional autoroute job (Java 21 => v2.1.0)
RUN curl -sSL -o /opt/freerouting.jar \
      https://github.com/freerouting/freerouting/releases/download/v2.1.0/freerouting-2.1.0.jar
# KiBot looks for `generate_interactive_bom.py` and otherwise DOWNLOADS it from GitHub at
# run time (flaky; failed the first hw-v0.1 release). Point it at the pinned pip install.
RUN ln -s /opt/kibot/bin/generate_interactive_bom /usr/local/bin/generate_interactive_bom.py
ENV PATH=/opt/kibot/bin:$PATH
