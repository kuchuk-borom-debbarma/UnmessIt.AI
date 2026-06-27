from kink import di
from src.infra.event_bus.adapters.in_memory_event_bus import InMemoryEventBus
from src.infra.langchain.json_llm import LLMJsonClient
from src.infra.settings import Settings
from src.infra.uuid_factory import UUIDFactory
from src.infra.vector.chroma_vector_store import ChromaVectorStoreImpl
from src.infra.vector.seai_vector_index import ChromaSEAIVectorIndex
from src.repositories.sqlite_dev_repository import SqliteDevRepository
from src.repositories.sqlite_ingest_repository import SqliteIngestRepository
from src.repositories.sqlite_memory_subject_repository import SqliteMemorySubjectRepository
from src.repositories.sqlite_retrieval_repository import SqliteRetrievalRepositoryImpl
from src.repositories.ports.memory_subject_repository import MemorySubjectRepository
from src.services.ingest_engine.ports.inbound.ingestor import Ingestor
from src.services.ingest_engine.domain.seai.chains.atom_code_verify_chain import AtomCodeVerifyChain
from src.services.ingest_engine.domain.seai.chains.atom_extract_chain import LLMAtomExtractor
from src.services.ingest_engine.domain.seai.chains.atom_verify_chain import LLMAtomVerifier
from src.services.ingest_engine.domain.seai.chains.episode_split_chain import LLMEpisodeSplitter
from src.services.ingest_engine.domain.seai.chains.episode_summary_chain import LLMEpisodeSummarizer
from src.services.ingest_engine.domain.seai.chains.episode_verify_chain import LLMEpisodeVerifier
from src.services.ingest_engine.domain.seai.chains.source_window_chain import SourceWindowChain
from src.services.ingest_engine.domain.seai.chains.strict_fastcoref_chain import NoopPreprocessor, StrictFastcorefPreprocessor
from src.services.ingest_engine.domain.seai.chains.subject_index_chain import SubjectIndexChain
from src.services.ingest_engine.domain.seai.ingestor import SEAIChains, SEAIIngestor
from src.services.ingest_engine.domain.seai.memory_subject_indexer import MemorySubjectIndexer
from src.services.ingest_engine.domain.seai.models import SEAIConfig
from src.services.ingest_engine.domain.seai.utils.evidence import EvidenceResolver
from src.services.retrieval_engine.domain.DeterministicRetrievalService import DeterministicRetrievalService
from src.services.retrieval_engine.domain.seai.answer_generator import StrictAnswerGenerator
from src.services.retrieval_engine.domain.seai.planner import QueryPlanner
from src.services.retrieval_engine.domain.seai.reranker import EvidenceReranker
from src.services.retrieval_engine.ports.outbound.VectorStoreContract import VectorStoreContract
from src.services.retrieval_engine.ports.outbound.RetrievalRepositoryContract import RetrievalRepositoryContract
from src.services.retrieval_engine.ports.inbound.RetrievalServiceContract import RetrievalServiceContract
from src.ports.event_bus import EventBus

def setup_di(settings: Settings):
    # Register global settings
    di[Settings] = settings
    di[EventBus] = InMemoryEventBus()
    
    # Register outbound adapters.
    di.factories[VectorStoreContract] = lambda di: ChromaVectorStoreImpl(settings=di[Settings])
    di.factories[RetrievalRepositoryContract] = lambda di: SqliteRetrievalRepositoryImpl()
    di.factories[MemorySubjectRepository] = lambda di: SqliteMemorySubjectRepository()
    di.factories[SqliteIngestRepository] = lambda di: SqliteIngestRepository()
    di.factories[SqliteDevRepository] = lambda di: SqliteDevRepository()
    
    # Register inbound use cases. SEAI chain order is assembled here, not in a hidden factory.
    di.factories[Ingestor] = _seai_ingestor
    di.factories[RetrievalServiceContract] = lambda di: DeterministicRetrievalService(
        vector_store=di[VectorStoreContract],
        retrieval_repo=di[RetrievalRepositoryContract],
        memory_subject_repo=di[MemorySubjectRepository],
        query_planner=QueryPlanner(LLMJsonClient(max_tokens=2048)),
        evidence_reranker=EvidenceReranker(LLMJsonClient(max_tokens=2048)),
        answer_generator=StrictAnswerGenerator(LLMJsonClient(max_tokens=2048)),
    )


def _seai_ingestor(di) -> SEAIIngestor:
    config = SEAIConfig()
    id_factory = UUIDFactory()
    json_client = LLMJsonClient()
    # One visible chain list keeps the ingest flow easy to reorder or trim.
    chains = SEAIChains(
        preprocess=StrictFastcorefPreprocessor() if config.enable_fastcoref else NoopPreprocessor(),
        window=SourceWindowChain(config),
        split_episodes=LLMEpisodeSplitter(json_client),
        summarize_episode=LLMEpisodeSummarizer(json_client, config.max_summary_words),
        verify_episode=LLMEpisodeVerifier(json_client),
        extract_atoms=LLMAtomExtractor(json_client),
        verify_atoms=LLMAtomVerifier(json_client),
        code_verify_atoms=AtomCodeVerifyChain(config, id_factory),
    )
    return SEAIIngestor(
        config=config,
        repository=di[SqliteIngestRepository],
        vector_indexer=ChromaSEAIVectorIndex(di[VectorStoreContract]),
        chains=chains,
        id_factory=id_factory,
        evidence_resolver=EvidenceResolver(),
        memory_subject_indexer=MemorySubjectIndexer(
            repository=di[MemorySubjectRepository],
            chain=SubjectIndexChain(json_client),
            id_factory=id_factory,
        ),
    )
