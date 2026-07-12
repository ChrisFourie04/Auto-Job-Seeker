"""Job source fetchers."""
from jobhunter.sources.remoteok import RemoteOKSource
from jobhunter.sources.remotive import RemotiveSource
from jobhunter.sources.weworkremotely import WeWorkRemotelySource
from jobhunter.sources.jobicy import JobicySource

ALL_SOURCES = [RemoteOKSource, RemotiveSource, WeWorkRemotelySource, JobicySource]

__all__ = ['ALL_SOURCES', 'RemoteOKSource', 'RemotiveSource', 'WeWorkRemotelySource', 'JobicySource']
