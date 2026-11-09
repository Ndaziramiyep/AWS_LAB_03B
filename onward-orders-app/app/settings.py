"""Release settings for the Onward Orders app. Change a value, push to main, and it ships."""

STUDENT_NAME = "Patrick Ndaziramiye"                       # Full name shown on the page (lab requirement)
LAB_NAME = "Delivering Order System Updates Safely"        # Lab name shown on the page (lab requirement)
RELEASE_NOTE = "Initial release"                           # Free text; edit it to demo a visible new version

# Demo switch for the "bad release" check: set True, push, and /health returns 500.
# The new (green) tasks never become healthy, the unhealthy-host alarm fires, and CodeDeploy
# rolls back automatically while the old (blue) tasks keep serving customers.
FORCE_UNHEALTHY = False                                    # Keep False for normal releases
