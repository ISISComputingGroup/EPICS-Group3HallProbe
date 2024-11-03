TOP=..
include $(TOP)/configure/CONFIG
#=======================================

# Install .dbd and .db files
DB += group3hallprobe.db
DB += group3hallprobe_probe.db
DATA += group3hallprobe.proto
DBD += group3hallprobe.dbd

# Sequence file
LIBRARY_IOC = group3hallprobe
group3hallprobe_SRCS += change_range.st
group3hallprobe_LIBS += seq pv
group3hallprobe_LIBS += $(EPICS_BASE_IOC_LIBS)

#=======================================
include $(TOP)/configure/RULES
