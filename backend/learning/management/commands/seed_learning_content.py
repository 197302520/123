from django.core.management.base import BaseCommand

from learning.models import Case, CourseModule, Dataset, PublishStatus


MODULES = [
    ("network-basics", "模块一：网络基础", "用图表示社会关系。"),
    ("network-measures", "模块二：网络测量", "比较中心性与网络结构。"),
    ("communities", "模块三：社区发现", "识别网络中的群体边界。"),
    ("diffusion", "模块四：扩散与传播", "观察信息与意见的传播。"),
    ("robustness", "模块五：鲁棒性", "分析网络面对攻击时的连通性。"),
    ("link-prediction", "模块六：链接预测", "从结构中推断潜在关系。"),
    ("dynamic-networks", "模块七：动态网络", "追踪关系与社群的时间变化。"),
]


class Command(BaseCommand):
    help = "Seed the seven published teaching modules and core case metadata."

    def handle(self, *args, **options):
        modules: dict[str, CourseModule] = {}
        for order, (slug, title, summary) in enumerate(MODULES, start=1):
            module, _ = CourseModule.objects.update_or_create(
                slug=slug,
                defaults={"title": title, "summary": summary, "order": order, "status": PublishStatus.PUBLISHED},
            )
            modules[slug] = module
        datasets = {}
        for slug, title, provenance, metadata in [
            ("zachary-karate", "Zachary 空手道俱乐部", "Zachary (1977)", {"nodes": 34, "edges": 78}),
            ("dolphins", "Dolphins 社交网络", "Lusseau et al. (2003)", {"nodes": 62, "edges": 159}),
        ]:
            dataset, _ = Dataset.objects.update_or_create(
                slug=slug,
                defaults={"title": title, "provenance": provenance, "metadata": metadata, "status": PublishStatus.PUBLISHED},
            )
            datasets[slug] = dataset
        for slug, title, summary, dataset_slug in [
            ("zachary-karate", "空手道俱乐部网络", "一个经典的社区发现案例。", "zachary-karate"),
            ("dolphins", "海豚社交网络", "观察海豚之间的社交关系。", "dolphins"),
        ]:
            Case.objects.update_or_create(
                slug=slug,
                defaults={
                    "module": modules["communities"], "dataset": datasets[dataset_slug], "title": title,
                    "summary": summary, "status": PublishStatus.PUBLISHED,
                },
            )
        self.stdout.write(self.style.SUCCESS("Seeded seven modules and two case metadata records."))
