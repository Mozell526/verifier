import {
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
  useHostTheme,
} from "cursor/canvas";

type Better = "new" | "old" | "split";
type Pattern =
  | "refuse_as_f"
  | "miss_or_wrong"
  | "bare_name"
  | "catalog"
  | "op_format"
  | "overstrict";

type Filter = "all" | Better | Pattern;

type CaseRow = {
  id: string;
  q: string;
  live: string;
  old: "F" | "NF" | "NE";
  neu: "F" | "NF" | "NE";
  pattern: Pattern;
  better: Better;
  spec: string;
  why: string;
};

const PATTERN_LABEL: Record<Pattern, string> = {
  refuse_as_f: "如实拒绝当办成",
  miss_or_wrong: "漏条件或改错值",
  bare_name: "裸词当姓名",
  catalog: "目录/枚举证据",
  op_format: "操作符或格式",
  overstrict: "过严或自相矛盾",
};

const BETTER_LABEL: Record<Better, string> = {
  new: "新更好",
  old: "旧更好",
  split: "互有对错",
};

const CASES: CaseRow[] = [
  { id: "I033", q: "平安伴同行", live: "空条件 + 活动暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§5/§7.1", why: "要结果没给；如实拒绝不能变 F。Authority 关着按 §3.1 核心未交付 → NF。" },
  { id: "I069", q: "去盘客", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§5/§7.1", why: "旧把「识别不支持并提示」写成 blocking 并判 F，正是 D3 已删口径。" },
  { id: "I088", q: "7月盘客", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§3.1", why: "核心筛选未交付；透明说明只能做 non-blocking。" },
  { id: "I093", q: "七月客户盘点", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§5", why: "盘点=要名单；没条件就是没办成。" },
  { id: "I114", q: "5月盘客客户", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§7.1", why: "旧明确写「能力边界不要求把缺失判为系统问题」——与协议相反。" },
  { id: "I149", q: "平安伴你行守护季", live: "空条件 + 活动暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§5", why: "活动季名称是明确业务对象；空条件 + 提示 ≠ 办成。" },
  { id: "I318", q: "盘客", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§7.1", why: "同族重复 case，口径稳定：新 NF / 旧 F。" },
  { id: "I377", q: "去盘客", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§7.1", why: "与 I069 同 query 同 live，分歧模式相同。" },
  { id: "I419", q: "盘客", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§7.1", why: "同族。" },
  { id: "I463", q: "去盘客", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§7.1", why: "同族。" },
  { id: "I481", q: "盘客", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§7.1", why: "同族。" },
  { id: "I495", q: "去盘客", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§7.1", why: "同族。" },
  { id: "I525", q: "盘客", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§3.1", why: "新也写了 is_supported=false，但仍把核心未交付判 NF，符合 Authority 关闭规则。" },
  { id: "I554", q: "去盘客", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§7.1", why: "同族。" },
  { id: "I626", q: "盘客", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§7.1", why: "同族。" },
  { id: "I633", q: "盘客", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§7.1", why: "同族。" },
  { id: "I643", q: "盘客", live: "空条件 + 盘客暂不支持", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.1/§7.1", why: "同族。" },
  { id: "I031", q: "牛龙，猴", live: "姓名牛龙；属相缺失 + 不支持提示", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §3.1/§6", why: "属相是并列核心维度；透明提示不能顶替 blocking 条件。" },
  { id: "I046", q: "去年购买了平安学业福", live: "abbrname 学业福；投保日缺失 + 提示", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.2/§6", why: "漏「去年」会扩大集合。更好，但与 I161 同场景新却判 F，口径不稳。" },
  { id: "I160", q: "姚礼芳7月到12月作为投保人，累计还有几份保单缴费？", live: "仅 applicantname=姚礼芳", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §4.2/§5", why: "日期范围和「还有几份」都没交付；旧把能力外维度写成 F。" },
  { id: "I213", q: "唐诗颖的生存金有没有领取？", live: "仅姓名唐诗颖", old: "F", neu: "NF", pattern: "refuse_as_f", better: "new", spec: "fulfilled §3 第一步/§7.8", why: "问的是领取状态（要答复），只定位姓名没回答；旧把该维降成 NE 后整体 F。" },

  { id: "I022", q: "少儿万能险", live: "pTypes=万能型", old: "F", neu: "NF", pattern: "miss_or_wrong", better: "new", spec: "fulfilled §4.2 · positioning 不变量2", why: "value_mappings 已登记少儿万能险→abbrname；泛化成万能型是改错值，不是等价替代。" },
  { id: "I084", q: "181…6669", live: "手机尾号 6669，无前缀", old: "F", neu: "NF", pattern: "miss_or_wrong", better: "new", spec: "fulfilled §4.2", why: "前缀 181 是明确约束且字段支持 prefix；只留尾号扩大集合。" },
  { id: "I125", q: "合家福客户", live: "agentPerspProductType=合家欢", old: "F", neu: "NF", pattern: "miss_or_wrong", better: "new", spec: "positioning §4/§8 · fulfilled §2.1", why: "目录无合家福、无映射；旧用系统归一化自我背书，正是 current_behavior 当尺子。" },
  { id: "I138", q: "查居养客户名单", live: "pajjmemberproductname EXISTS", old: "F", neu: "NF", pattern: "miss_or_wrong", better: "new", spec: "positioning 不变量2", why: "居养应对会员等级/版本；EXISTS 服务线是选错字段，空间代理不能证明这次选对。" },
  { id: "I154", q: "张小岗这个月增加多少保费可以享受居养", live: "姓名 + 潜客", old: "F", neu: "NF", pattern: "miss_or_wrong", better: "new", spec: "fulfilled §4.2 · positioning §8.2", why: "多了未表达的潜客限制，居养目标落到状态字段。" },
  { id: "I155", q: "老客户这个月可以增加保费升级到居养的客户", live: "仅潜客", old: "F", neu: "NF", pattern: "miss_or_wrong", better: "new", spec: "fulfilled §4.2", why: "老客户 / 本月增费 / 升级都丢了，只剩增强规则里的潜客。" },
  { id: "I230", q: "没有医疗险的寿险客户", live: "pCategorys NOT_CONTAINS 医疗；plantypedesc MATCH 寿险", old: "F", neu: "NF", pattern: "miss_or_wrong", better: "new", spec: "positioning §4 inlive_boundary", why: "寿险字段已 Load 只支持 CONTAINS/NOT_CONTAINS；MATCH 超出操作符空间。" },
  { id: "I248", q: "红莲保单", live: "searchClientName=红莲", old: "F", neu: "NF", pattern: "miss_or_wrong", better: "new", spec: "fulfilled §4.2", why: "业务对象是保单，不是姓名；旧跟「姓名-保单上下文」增强规则走，系统行为自证。" },
  { id: "I387", q: "我名下所有客户投的重疾险", live: "pCategorys MATCH 疾病保险", old: "F", neu: "NF", pattern: "miss_or_wrong", better: "new", spec: "fulfilled §4.2", why: "「我名下所有」未落到 isBuyInsurance 全量枚举；险种对了但范围丢了。" },

  { id: "I120", q: "VIE。", live: "searchClientName=VIE", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1 · positioning §4", why: "无姓名指示、无独立人名证据；旧用增强规则证明映射正确。" },
  { id: "I168", q: "傻生", live: "searchClientName=傻生", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1", why: "「傻」非姓，目录无人名证据；抽出姓名是无依据收窄。" },
  { id: "I175", q: "ZHANG", live: "searchClientName=ZHANG", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1 · positioning §5.4", why: "英文裸词；增强规则不是信任根。" },
  { id: "I176", q: "ZHANG", live: "searchClientName=ZHANG", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1", why: "与 I175 同 query 同 live。" },
  { id: "I184", q: "高", live: "searchClientName 前缀 高", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "positioning §4 current_behavior", why: "百家姓前缀规则是系统行为；缺独立姓氏资料时不能 F。" },
  { id: "I190", q: "WU", live: "searchClientName=WU", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1", why: "英文裸词，无独立人名证据。" },
  { id: "I194", q: "huhancheng", live: "searchClientName=huhancheng", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1", why: "拼音连写裸词，旧按英文姓名规则直接 F。" },
  { id: "I206", q: "YULIHUANG", live: "searchClientName=YULIHUANG", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1", why: "同族英文裸词。" },
  { id: "I240", q: "LIUDAN", live: "searchClientName=LIUDAN", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1", why: "同族。" },
  { id: "I247", q: "WangOu", live: "searchClientName=WangOu", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1", why: "同族。" },
  { id: "I260", q: "Jian", live: "searchClientName=Jian", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1", why: "同族。" },
  { id: "I264", q: "YULIHUANG", live: "searchClientName=YULIHUANG", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1", why: "与 I206 重复。" },
  { id: "I344", q: "查金风", live: "searchClientName=金风", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1", why: "「查」是外壳；金风也可能是金凤产品，姓名证据不够。" },
  { id: "I358", q: "见光", live: "searchClientName=见光", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1", why: "二字词无姓名指示，也可能是产品/活动。" },
  { id: "I535", q: "任", live: "searchClientName 前缀 任", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "positioning §4", why: "与「高」同类：单字姓规则不能自我证明。" },
  { id: "I650", q: "共展", live: "searchClientName=共展", old: "F", neu: "NF", pattern: "bare_name", better: "new", spec: "fulfilled §2.1", why: "更像业务词，不是能确认的人名。" },
  { id: "I485", q: "昊轩", live: "searchClientName=昊轩", old: "F", neu: "NF", pattern: "bare_name", better: "split", spec: "fulfilled §2.1 vs §3.1", why: "二字中文名形态很像人名。新要求目录级人名证据，对姓名场过严；旧又用增强规则自证。两边都不干净。" },
  { id: "I539", q: "王坤林", live: "searchClientName=王坤林", old: "F", neu: "NF", pattern: "bare_name", better: "split", spec: "fulfilled §2.1 vs §3.1", why: "三字「姓+名」是客户搜索最常见形态。新若把这类也打 NF，会系统误伤；旧 F 的证据链仍偏弱。" },

  { id: "I210", q: "金凤", live: "abbrname MATCH 金凤", old: "NF", neu: "F", pattern: "catalog", better: "new", spec: "positioning §4 inlive_boundary", why: "目录确认金凤是投保险种简称精确枚举；旧当歧义裸词打 NF。" },
  { id: "I211", q: "金凤", live: "abbrname MATCH 金凤", old: "NF", neu: "F", pattern: "catalog", better: "new", spec: "positioning §4", why: "与 I210 同 live。旧还把枚举有效性打成 NE。" },
  { id: "I231", q: "金凤", live: "abbrname MATCH 金凤", old: "NF", neu: "F", pattern: "catalog", better: "new", spec: "positioning §4", why: "同族。" },
  { id: "I232", q: "金凤", live: "abbrname MATCH 金凤", old: "NF", neu: "F", pattern: "catalog", better: "new", spec: "positioning §4", why: "同族。旧抱怨枚举为空，新用已 Load 枚举文件。" },
  { id: "I239", q: "金凤", live: "abbrname MATCH 金凤", old: "NF", neu: "F", pattern: "catalog", better: "new", spec: "positioning §4", why: "同族。" },
  { id: "I236", q: "宝贝卡", live: "abbrname MATCH 宝贝卡", old: "NE", neu: "F", pattern: "catalog", better: "new", spec: "fulfilled §3.1 · positioning §4", why: "旧因枚举未列出打 NE；Authority 关闭不得用缺枚举逃到 NE。新有目录 exact 成员。" },
  { id: "I416", q: "满意", live: "abbrname MATCH 满意", old: "NF", neu: "F", pattern: "catalog", better: "new", spec: "positioning §4", why: "权威 abbrname 枚举 exact 命中；旧当未验证枚举打 NF。" },
  { id: "I123", q: "生效日期是2026年1月1号以后的保单，且剔除百万医疗客户", live: "poleffdate GTE 2026-01-01 + 百万医疗 NOT_CONTAINS", old: "NF", neu: "F", pattern: "catalog", better: "new", spec: "fulfilled §4.3", why: "旧抠「以后=GT」；GTE 含当日是合理等价，百万医疗枚举也对齐。" },
  { id: "I161", q: "林秀微去年投保全家保的客户", live: "投保人林秀微 + 全家保；日期提示不支持", old: "NF", neu: "F", pattern: "catalog", better: "split", spec: "fulfilled §4.2 vs I046", why: "投保人角色新读得对。但「去年」与 I046 同是不支持投保日，这里新却不挡 F，口径打架。" },

  { id: "I008", q: "在我这买过保险的投保人都有谁", live: "isBuyInsurance + applicantname EXISTS", old: "NF", neu: "F", pattern: "op_format", better: "old", spec: "positioning §4 不变量2", why: "字段只允许 MATCH，EXISTS 超出操作符空间。新按语义放行，等于升级了「这次选哪个」。" },
  { id: "I131", q: "身份证已过期的投保人", live: "idValidDate LTE + applicantname EXISTS", old: "NF", neu: "F", pattern: "op_format", better: "old", spec: "fulfilled §4.2 · positioning §4", why: "漏证件类型「身份证」，EXISTS 再次越界。新把 idType 解释成不该加。" },
  { id: "I241", q: "C0004533449897", live: "clientNo MATCH 该值", old: "NF", neu: "F", pattern: "op_format", better: "old", spec: "positioning inlive_boundary", why: "C 后 13 位超出客户号格式空间；生成越界值不应 F。" },
  { id: "I277", q: "C0O……513", live: "空条件 + 未识别", old: "NF", neu: "F", pattern: "op_format", better: "old", spec: "fulfilled §4.5", why: "C 前缀掩码可抽尾号 513；新误读成残缺保单号，把空条件判 F。" },

  { id: "I034", q: "大写P07。六个零。", live: "空条件 + 未识别", old: "F", neu: "NF", pattern: "overstrict", better: "old", spec: "positioning 空间 / fulfilled §4.1", why: "P07000000 长度不像合法保单号。旧拒绝生成是守空间；新要求必须 MATCH 出去。" },
  { id: "I263", q: "小雨弟弟", live: "小雨 + 兄弟姐妹 + 男", old: "F", neu: "NF", pattern: "overstrict", better: "old", spec: "fulfilled §4.3 / positioning 不变量2", why: "弟弟的可表达代理已是关系+性别。新额外要「年龄小于本人」，当前空间未必达得到。" },
  { id: "I288", q: "配", live: "空条件 + 未识别", old: "F", neu: "NF", pattern: "overstrict", better: "old", spec: "fulfilled §2.1 内部一致性", why: "新对「高/任」因裸词打 NF，对「配」又要求模糊姓名匹配，自相矛盾。" },
  { id: "I616", q: "海蜂老板娘周老板", live: "空条件 + 未识别", old: "F", neu: "NF", pattern: "overstrict", better: "old", spec: "fulfilled §2.1", why: "周老板是称谓不是自然人姓名；新要求抽姓名，旧不误抽更稳。" },
  { id: "I638", q: "C00OO731392", live: "clientNo OR polNo 同值", old: "F", neu: "NF", pattern: "overstrict", better: "old", spec: "fulfilled §4.2 弱", why: "多一个 OR polNo。C 前缀通常进不了保单号空间，结果集几乎不变；新按「多字段」打 NF 偏紧。" },
];

const LIVE_DIFFS = [
  ["I013", "17或18岁", "两条 Age=17/18", "一条 Age 17–18", "NF / NF", "排除：live 条件形态不同"],
  ["I102", "18", "仅 Age=18", "被保人姓名18 + Age=18", "NF / NF", "排除：新 live 多了姓名条件"],
  ["I122", "多条潜客线", "6 条会员潜客 AND", "仅平安居家潜客", "F / F", "排除：条件集合不同，但两边都判 F"],
  ["I135", "有保单生效日", "仅 poleffdate EXISTS", "EXISTS + 客户/准客", "F / NF", "排除：新 live 多了客户类型"],
  ["I150", "保单到期日约一个月", "max 2026-09-14", "max 2026-09-13", "NF / NF", "排除：日期上界差一天"],
  ["I267", "2026年寿险", "寿险 + 2026生效", "仅 2026 生效", "F / NF", "排除：新 live 丢了寿险"],
  ["I274", "财富+医疗", "医疗 AND 财富", "财富 AND 医疗", "F / F", "仅顺序，算同 live"],
  ["I290", "18岁男女?", "仅 Age=18", "Age=18 + 男 + 女", "F / NF", "排除：新 live 多了互斥性别"],
  ["I317", "子女年龄段", "空条件", "子女 + 生日范围", "NF / NF", "排除：一边空、一边有条件"],
  ["I349", "年缴≥60万", "仅 annPremSegNum", "有险种 EXISTS + 年缴", "NF / NF", "排除：新 live 多了 EXISTS"],
  ["I353", "万能型有效保单", "万能型 + 保单状态枚举", "仅万能型", "F / NF", "排除：新 live 丢了状态"],
];

function matchesFilter(row: CaseRow, filter: Filter): boolean {
  if (filter === "all") return true;
  if (filter === "new" || filter === "old" || filter === "split") return row.better === filter;
  return row.pattern === filter;
}

function Status({ value }: { value: "F" | "NF" | "NE" }) {
  const theme = useHostTheme();
  const color =
    value === "F" ? theme.accent.primary : value === "NF" ? theme.text.secondary : theme.text.tertiary;
  return (
    <Text as="span" size="small" weight="semibold" style={{ color }}>
      {value}
    </Text>
  );
}

function CaseExamples({ items }: { items: string[] }) {
  return (
    <Stack gap={2}>
      {items.map((line) => (
        <Text size="small">{line}</Text>
      ))}
    </Stack>
  );
}

export default function ClientSearchJudgeCompare() {
  const theme = useHostTheme();
  const [filter, setFilter] = useCanvasState<Filter>("filter", "all");
  const visible = CASES.filter((row) => matchesFilter(row, filter));
  const nNew = CASES.filter((r) => r.better === "new").length;
  const nOld = CASES.filter((r) => r.better === "old").length;
  const nSplit = CASES.filter((r) => r.better === "split").length;

  const filters: { id: Filter; label: string }[] = [
    { id: "all", label: `全部 ${CASES.length}` },
    { id: "new", label: `新更好 ${nNew}` },
    { id: "old", label: `旧更好 ${nOld}` },
    { id: "split", label: `互有对错 ${nSplit}` },
    { id: "refuse_as_f", label: "如实拒绝当F" },
    { id: "miss_or_wrong", label: "漏/错条件" },
    { id: "bare_name", label: "裸词姓名" },
    { id: "catalog", label: "目录证据" },
    { id: "op_format", label: "操作符格式" },
    { id: "overstrict", label: "过严" },
  ];

  return (
    <Stack gap={28} style={{ padding: 24, maxWidth: 1180 }}>
      <Stack gap={8}>
        <H1>client_search 新旧 judge 对比</H1>
        <Text tone="secondary">
          新 judge：verifier-client_search-cases-20260814-185013.xlsx · 旧 judge：20260814-205846.xlsx ·
          尺子：fulfilled.md、material-positioning.md · 只分析，不改代码
        </Text>
      </Stack>

      <Callout tone="success" title="结论：同 live 下，新 judge 整体更好">
        主因是纠正了 fulfilled.md 明确禁止的「如实拒绝 / 能力外透明降级 = 办成了」。
        66 条同 live 分歧里，新更好 54、旧更好 9、互有对错 3。
        新的代价是裸词姓名过严，以及「去年投保日不支持」在 I046 / I161 口径不一致。
      </Callout>

      <Grid columns={4} gap={16}>
        <Stat value="331 / 341" label="同 live（条件+文案+code）" tone="success" />
        <Stat value="66" label="同 live 且 judge 不同" tone="warning" />
        <Stat value="54" label="新更好" tone="success" />
        <Stat value="9" label="旧更好" tone="danger" />
      </Grid>

      <Stack gap={10}>
        <H2>1. Live 是不是同一批</H2>
        <Text>
          是同一批 query，也基本是同一批 live 输出。341 条 user_text 全相同；输入只差新表多了空的
          extra_input_params。输出里 330 条 conditions / robot_text / code 完全一致，I274 只是条件顺序对调。
          其余大量差异是 cost_times 和 matched_patterns，不改变被评语义。
        </Text>
        <Text>
          有 10 条 live 行为实质不同（LLM 不稳：多条件、少条件、日期上界差一天）。其中 4 条连带
          judge 也不同（I135 / I267 / I290 / I353），下面 judge 表不收入，避免把 live 差算成 judge 差。
        </Text>
        <Table
          headers={["核对项", "结果"]}
          rows={[
            ["用例数 / ID 对齐", "两边各 341，ID 全集相同"],
            ["user_text", "341 / 341 相同"],
            ["conditions + robot_text + code", "330 完全相同 + 1 条仅顺序（I274）"],
            ["实质 live 差", "10 条，见文末附表"],
            ["易变字段", "cost_times 333 条不同；matched_patterns 106 条不同"],
          ]}
        />
      </Stack>

      <Stack gap={10}>
        <H2>2. 同 live 上的三态位移</H2>
        <Text tone="secondary">
          331 条同 live。旧更宽：F 252 / NF 78 / NE 1。新更严：F 212 / NF 119 / NE 0。
          分歧 66 条：旧 F→新 NF 53，旧 NF→新 F 12，旧 NE→新 F 1。
        </Text>
        <BarChart
          height={220}
          categories={["fulfilled", "not_fulfilled", "not_evaluable"]}
          series={[
            { name: "旧 judge（同 live）", data: [252, 78, 1], tone: "neutral" },
            { name: "新 judge（同 live）", data: [212, 119, 0], tone: "info" },
          ]}
        />
        <Text size="small" tone="tertiary">
          Source: 两份 xlsx 的 状态 / overall_fulfillment.status · 同 live 331 条 · 2026-08-14
        </Text>
      </Stack>

      <Stack gap={10}>
        <H2>3. 分歧按模式</H2>
        <Text>
          旧 judge 的主 bug 是把「能力边界 + 如实提示」写成 blocking 并判 F，直接撞
          fulfilled §7.1 / §5 / D3。新 judge 在 Authority 关闭时按 §3.1 走：核心没交付就 NF，提示只做
          non-blocking。这是最大净胜。
        </Text>
        <BarChart
          horizontal
          height={240}
          categories={[
            "如实拒绝当F",
            "裸词当姓名",
            "漏/错条件",
            "目录/枚举",
            "过严或矛盾",
            "操作符/格式",
          ]}
          series={[{ name: "同 live 分歧条数", data: [21, 18, 9, 9, 5, 4], tone: "info" }]}
        />
        <Text size="small" tone="tertiary">
          条数按上表 66 条归类 · 如实拒绝含 17 条盘客/活动重复 case
        </Text>
        <Table
          headers={["模式", "条数", "典型位移", "谁更好", "协议点", "case 示例"]}
          rows={[
            [
              "如实拒绝当办成",
              "21",
              "旧 F → 新 NF",
              "新",
              "fulfilled §4.1 §5 §7.1；Authority 关 §3.1",
              <CaseExamples
                items={[
                  "I069  去盘客",
                  "I033  平安伴同行",
                  "I046  我想查询去年购买了平安学业福的客户名单。",
                  "I213  唐诗颖的生存金有没有领取？",
                ]}
              />,
            ],
            [
              "裸词当姓名",
              "18",
              "旧 F → 新 NF",
              "新为主，2 条过严",
              "§2.1 无证据不得 F；增强规则 ≠ 信任根",
              <CaseExamples
                items={[
                  "I120  VIE。",
                  "I175  ZHANG",
                  "I650  共展",
                  "I539  王坤林（过严）",
                ]}
              />,
            ],
            [
              "漏条件或改错值",
              "9",
              "旧 F → 新 NF",
              "新",
              "§4.2；positioning 不升级「这次选哪个」",
              <CaseExamples
                items={[
                  "I022  少儿万能险",
                  "I125  合家福客户",
                  "I248  红莲保单",
                  "I084  181…6669",
                ]}
              />,
            ],
            [
              "目录/枚举证据",
              "9",
              "旧 NF/NE → 新 F",
              "新，1 条口径打架",
              "inlive_boundary 只升级空间",
              <CaseExamples
                items={[
                  "I210  金凤",
                  "I236  宝贝卡",
                  "I416  满意",
                  "I161  林秀微去年投保全家保的客户（口径打架）",
                ]}
              />,
            ],
            [
              "过严或自相矛盾",
              "5",
              "旧 F → 新 NF",
              "旧",
              "新内部口径不稳",
              <CaseExamples
                items={[
                  "I034  大写P07。六个零。",
                  "I288  配",
                  "I616  海蜂老板娘周老板",
                  "I263  小雨弟弟",
                ]}
              />,
            ],
            [
              "操作符或格式",
              "4",
              "旧 NF → 新 F",
              "旧",
              "EXISTS/越界格式超出空间",
              <CaseExamples
                items={[
                  "I008  在我这买过保险的投保人都有谁",
                  "I131  身份证已过期的投保人",
                  "I241  C0004533449897",
                  "I277  C0O……513",
                ]}
              />,
            ],
          ]}
          rowTone={["success", "success", "success", "success", "warning", "warning"]}
          striped
        />
      </Stack>

      <Stack gap={10}>
        <H2>4. 新 judge 的两处代价</H2>
        <Grid columns={2} gap={16}>
          <Card>
            <CardHeader>裸词姓名一把尺量到底</CardHeader>
            <CardBody>
              <Text>
                对 VIE / ZHANG / 共展 这类无证据映射，新判 NF 对。但 王坤林、昊轩 也按「目录无人名证据」打
                NF，客户搜索最常见的中文姓名会被系统误伤。旧的问题是反过来：用能力清单增强规则当证明。
              </Text>
            </CardBody>
          </Card>
          <Card>
            <CardHeader>「不支持字段」口径不稳</CardHeader>
            <CardBody>
              <Text>
                I046「去年 + 学业福」新因漏日期判 NF；I161「去年 + 全家保」新把同一类不支持投保日当成非阻塞并判
                F。盘客族倒是稳定 NF。说明新 judge 不是规则机，同一协议点仍会漂。
              </Text>
            </CardBody>
          </Card>
        </Grid>
        <Callout tone="warning" title="旧更好的 9 条不该被平均掉">
          I008 / I131 的 EXISTS 超出字段操作符空间；I241 客户号超长；I277 掩码尾号可抽却空条件；I034
          非法保单号不该强交；I288 与裸词规则相反；I616 称谓不当姓名。这些是 positioning
          「只升级空间、不升级选择」上新 judge 松了。
        </Callout>
      </Stack>

      <Stack gap={10}>
        <H2>5. 互有对错 / 过严：新 judge 问题从哪来</H2>
        <Text>
          这 8 条不是「新 judge 更严所以更好」。问题都出在 draft judge 系统提示内部几条指令互相打架，模型每次只咬住其中一句。
          源文件：`impl/projects/client_search/draft/judge.py` 约 1479–1525 行。
        </Text>
        <Callout tone="info" title="四条指令同时在场">
          裸词规则要独立人名证据才能 F；字段 notes 又说 2–4 字中文形态可以出姓名；意图拆解要求每个维度一条
          expectation；空条件且有「明确业务对象」必须 NF，且「拒绝越界」不能当 blocking 核心。模型无法同时守住。
        </Callout>
        <Table
          stickyHeader
          striped
          headers={["Case", "类", "新的问题", "机制", "来源引用"]}
          rowTone={["warning", "warning", "warning", "danger", "danger", "danger", "danger", "danger"]}
          rows={[
            [
              "I485 昊轩\nI539 王坤林",
              "互有对错",
              "把常见 2/3 字中文名也打成「无人名证据 → NF」，并要求澄清。客户搜索最常见形态被系统误伤。",
              "只执行了裸词规则前半句，丢掉括号里的「或该形态就是姓名检索」。字段 notes 的 2–4 字形态本可当形态证据，被「字段定义只证明字段语义」一票否决。",
              <CaseExamples
                items={[
                  "draft/judge.py §裸词规则 L1504-1508",
                  "「独立姓名证据指资料明确该 token 是人名（或该形态就是姓名检索）」",
                  "draft/judge.py §证据分级 L1497",
                  "「字段定义只证明该字段声明的语义」",
                  "capability_manifest.searchClientName notes",
                  "「无法确认是自然人人名时宁可不输出；默认中文姓名结构为2至4字，或明确姓名指示词引出」",
                  "新 judge JSON I539 boundary",
                  "bare_token_requires_independent_name_evidence=true；acceptance 要求「存在独立证据确认后才可输出」",
                ]}
              />,
            ],
            [
              "I161 林秀微去年投保全家保\n对照 I046 去年+学业福",
              "互有对错",
              "同一类「投保日 is_supported=false + 透明提示」，I046 把「去年」做成 blocking 核心打 NF，I161 做成 blocking=false 透明说明后整体 F。",
              "提示里同时写了「说明不能替代核心结果」和「透明说明必须另建 blocking=false」。拆 expectation 时 blocking 标签由模型自选，没有代码约束。",
              <CaseExamples
                items={[
                  "draft/judge.py L1512",
                  "「is_supported=false … 分别评价核心交付与透明边界说明，不能用说明替代核心结果」",
                  "draft/judge.py L1522-1524",
                  "「安全拒绝和透明说明必须另建 blocking=false」",
                  "「被遗漏的 blocking 维度按实际未交付判 not_fulfilled」",
                  "I161 expectation「投保日期去年约束的透明说明」blocking=false",
                  "boundary.note：「不纳入可评价系统错误」",
                  "I046 expectation「按去年投保时间筛选客户」blocking=true → NF",
                ]}
              />,
            ],
            [
              "I263 小雨弟弟",
              "过严",
              "姓名+兄弟姐妹+男都对了，仍因「弟弟=年龄小于本人」缺失打 NF。当前空间没有相对年龄字段。",
              "意图拆解「每个可独立判断的请求维度拆一条」被用成常识扩维。缺的年龄条件来自模型猜测，不是 actual / catalog。",
              <CaseExamples
                items={[
                  "draft/judge.py §意图拆解 L1479-1481",
                  "「每个可独立判断的请求维度拆一条 expectation」",
                  "draft/judge.py §逐项核对 L1485",
                  "「wrong/missing/extra 必须来自当前 actual，不能来自猜测」——本条违反了自己",
                  "I263 evidence 只有三条 actual 条件，无家庭相对年龄 Load",
                  "material-positioning §4 不变量2：只升级空间，不升级这次选哪个",
                ]}
              />,
            ],
            [
              "I288 配",
              "过严",
              "对「高/任/昊轩」因裸词打 NF，对单字「配」又要求必须输出姓名模糊匹配。自相矛盾。",
              "把低优先级兜底规则「姓名-模糊匹配 1–3 字」当成必须交付的二级证据。同一条规则在权益/关爱上被自己写成「过度捕获、不能当人名证据」。",
              <CaseExamples
                items={[
                  "I288 evidence：key=姓名-模糊匹配，patterns=[单个至三个中文字符]",
                  "draft/judge.py §证据分级 L1493-1496",
                  "enhanced_rules 被列为可支撑 F 的二级证据；matched_pattern 是不能单独撑 F 的三级",
                  "模型把三级 path match 抬成了「应生成条件」的二级",
                  "draft/judge.py §裸词规则 L1505-1508",
                  "「Reference/path match alone is not intent proof」",
                  "history/052：enhanced_rules.姓名-模糊匹配 priority 1「会把任意1至3个中文字符捕获为姓名」，「不应覆盖宁可不输出」",
                ]}
              />,
            ],
            [
              "I034 大写P07。六个零。",
              "过严",
              "P07000000 不像合法保单号长度，空条件拒绝更合理；新要求必须 MATCH 出去。",
              "「拒绝越界请求」被禁止当 blocking 核心；「有明确业务对象但无条件 → NF」把口述编号当成必须交付的对象。只 Load 了 polNo 支持 MATCH，没核格式空间。",
              <CaseExamples
                items={[
                  "draft/judge.py L1513-1519",
                  "「以下内容永远不能单独成为 blocking 核心交付：…拒绝越界请求、告知当前限制、未识别到条件」",
                  "「若请求存在明确业务对象但 actual 没有可执行条件…按当前交付判 not_fulfilled」",
                  "I034 evidence：loaded_field_definition polNo operators=[MATCH]，无长度/格式",
                  "对照旧 judge：长度不符合 polNo 格式 → 不生成条件（守 inlive 空间）",
                  "positioning §4：空间外值是发现信号，不是该交出去的条件",
                ]}
              />,
            ],
            [
              "I616 海蜂老板娘周老板",
              "过严",
              "把称谓「周老板」当成必须交付的客户姓名；空条件拒绝更稳。",
              "与 I034 同一条「明确业务对象必须有可执行条件」。evidence 是空对象，没有任何独立人名证据，直接违反裸词规则。",
              <CaseExamples
                items={[
                  "draft/judge.py L1514-1519 明确业务对象 + 空条件 → NF",
                  "I616 evidence：query + 空 {} + result_set_verified=false，无 Catalog Load",
                  "draft/judge.py §裸词规则 L1506-1508",
                  "「live 把它写成姓名…都不够支撑 fulfilled」——这里连 live 都没写成姓名",
                  "searchClientName notes：业务名词/无法确认时宁可不输出；称谓不是自然人姓名",
                ]}
              />,
            ],
            [
              "I638 C00OO731392",
              "过严",
              "clientNo 已对，OR 多一个 polNo 被打 NF。C 前缀通常进不了保单号空间，结果集几乎不变。",
              "提示写的是「无依据的额外收窄」判 NF。OR 是扩大不是收窄，模型把「改变集合」都算 extra。意图拆解又拆出一条 blocking「避免增加未表达的保单号」。",
              <CaseExamples
                items={[
                  "draft/judge.py §逐项核对 L1484",
                  "「条件缺失、错误映射、无依据的额外收窄分别判 not_fulfilled」",
                  "I638 reasoning：「额外加入 polNo，扩大了未表达的检索范围」——用收窄条款打扩大",
                  "draft/judge.py L1481 每个维度一条 expectation → 多造了一条 blocking",
                ]}
              />,
            ],
          ]}
        />
        <Text size="small" tone="tertiary">
          源：新 judge xlsx 185013 的 Judge JSON（expectation / evidence / reasoning）对 draft/judge.py 系统提示 · 2026-08-14
        </Text>
        <H3>这 8 条收成 4 个根因</H3>
        <Table
          headers={["根因", "伤到的 case", "改哪里才断得掉"]}
          rows={[
            [
              "裸词规则只写了「要独立证据」，形态条款被证据分级吃掉",
              "I485 I539；反向误用同一规则 → I288 I616",
              "把「2–4 字中文姓名形态」写成可 F 的独立姓名证据；模糊匹配规则降回三级，不得要求必须输出",
            ],
            [
              "is_supported=false 的 blocking 标签由模型自选",
              "I161 vs I046",
              "不支持字段的遗漏维度统一：要么全是 blocking NF，要么全是 non-blocking 说明，禁止同轮两种拆法",
            ],
            [
              "意图拆解没有「空间里有没有这个维度」闸门",
              "I263；连带 I638 多造 blocking",
              "拆 expectation 前先问：当前 inlive 空间能否表达。表达不了的常识维不得做 blocking",
            ],
            [
              "「明确对象 + 空条件 = NF」盖住了合法拒识",
              "I034 I616",
              "越界/称谓/格式外本就不可执行时，空条件 + 未识别应允许 F 或至少不因「没交出去」打 NF",
            ],
          ]}
          rowTone={["warning", "warning", "warning", "warning"]}
        />
      </Stack>

      <Stack gap={12}>
        <H2>6. 同 live、judge 不同的 66 条</H2>
        <Text tone="secondary">
          状态缩写 F=fulfilled，NF=not_fulfilled，NE=not_evaluable。行色：绿=新更好，红=旧更好，黄=互有对错。
        </Text>
        <Row gap={8} wrap>
          {filters.map((item) => (
            <Pill active={filter === item.id} onClick={() => setFilter(item.id)}>
              {item.label}
            </Pill>
          ))}
        </Row>
        <Text size="small" tone="tertiary">
          当前 {visible.length} 条
        </Text>
        <Table
          stickyHeader
          striped
          headers={["ID", "用户输入", "Live", "旧", "新", "模式", "更好", "依据与理由"]}
          columnAlign={["left", "left", "left", "center", "center", "left", "left", "left"]}
          rowTone={visible.map((row) =>
            row.better === "new" ? "success" : row.better === "old" ? "danger" : "warning",
          )}
          rows={visible.map((row) => [
            row.id,
            row.q,
            row.live,
            <Status value={row.old} />,
            <Status value={row.neu} />,
            PATTERN_LABEL[row.pattern],
            BETTER_LABEL[row.better],
            `${row.spec}。${row.why}`,
          ])}
        />
      </Stack>

      <Stack gap={10}>
        <H2>7. 怎么优化，以及会误伤什么</H2>
        <Callout tone="warning" title="这批是 bad case，不能拿它当唯一准星">
          341 条全是 Scenario=badcase。盘客/活动、裸词业务词、残号、称谓被放大了；正常流量里占大头的是「王坤林」「张三+产品」「合法保单号」。
          在这张表上把 NF 再推高，看起来像修好了过严以外的所有问题，到正常场景会把姓名检索系统误伤。
          下面每条方案都先写能修什么，再写会误伤哪类正常 query。
        </Callout>

        <H3>先不要做的</H3>
        <Table
          headers={["做法", "看起来能修", "实际误伤"]}
          rows={[
            [
              "再往 prompt 里加几句「例外」",
              "I046/I161、裸词、空条件各补一句",
              "现在就是句子互相打架。再加句子，模型继续每次只咬一句，分歧会换一批 case 出现",
            ],
            [
              "要求有「姓名/叫/名叫」才准姓名 F",
              "VIE、权益、共展、配",
              "正常场景里大量是裸名「王坤林」「昊轩」。这是最典型的 badcase 过拟合",
            ],
            [
              "不支持字段一律 blocking NF",
              "盘客族、I046",
              "「张三的学业福，去年买的」这类正常混合问，附带一个不支持日期就整案 NF，召回正常 F 会塌",
            ],
            [
              "只拿本 xlsx 的 66 条分歧当回归闸",
              "过严 8 条会好看",
              "新更好的 54 条（盘客 NF、少儿万能、合家福）可能被一起改回去，而且看不见正常姓名 F 的退化",
            ],
          ]}
          rowTone={["danger", "danger", "danger", "danger"]}
        />

        <H3>可以做的方案</H3>
        <Table
          stickyHeader
          striped
          headers={["方案", "修哪类问题", "做法", "会误伤什么", "对 badcase / 正常场景"]}
          rows={[
            [
              "A. 姓名形态条款写死，不再只认目录人名",
              "I485 昊轩、I539 王坤林 过严",
              "独立姓名证据 = 资料点名该 token 是人名，或 2–4 字中文且未命中产品/活动/枚举。英文裸词、单字、称谓仍不能单靠形态 F。",
              "2–3 字业务词：共展、见光、金风、年华、生存金、权益。目录没覆盖到的产品简称会被当成姓名 F。",
              "badcase 上会放回一批「假姓名」F；正常场景姓名召回会明显好。必须配方案 B，否则 A 单独上会吐回旧 judge 的姓名误 F。",
            ],
            [
              "B. 目录/枚举先消歧，模糊匹配永不要求输出",
              "I288 配 自相矛盾；金凤/满意 那侧要保住",
              "token 先搜 abbrname/活动/字段枚举。命中 → 按空间物；未命中再走 A。姓名-模糊匹配只解释 live 怎么生成，不得写成「应生成姓名条件」。",
              "人名碰巧等于产品简称（客户就叫「满意」「金凤」）会被判成产品 F，姓名漏检。枚举不全时，真产品会落到 A 被当成姓名。",
              "badcase 里产品裸词（金凤/宝贝卡/满意）继续对；正常「查金凤」若是找人会被误伤。枚举要当空间代理，不能当「这次选得对」的唯一尺子。",
            ],
            [
              "C. 核心对象 vs 附加约束，blocking 不准模型自选",
              "I161 vs I046 口径漂；盘客族要保住 NF",
              "唯一核心业务对象缺失（盘客/活动/属相是整句要找的东西）→ blocking NF。已交付主对象后的不支持附加维（去年、生存金状态）→ 固定 non-blocking 说明，不得改整体 F/NF。用代码或固定 schema 打标，不靠再写一段 prompt。",
              "「去年购买学业福」里「去年」算不算核心，人也会吵。标成附加，会漏掉时间被丢掉、集合被放大；标成核心，正常「带一句日期」的问法会整案 NF。",
              "badcase 盘客/活动仍然 NF（这是这张表的主净胜，不能吐回去）。正常「姓名+产品+随口日期」能保住 F。坑在核心/附加的划界，要写死规则：仅当该维是整句唯一对象，或去掉后目标集合从「某类人」变成「所有人」时才 blocking。",
            ],
            [
              "D. 拆 expectation 前过空间闸",
              "I263 弟弟年龄；I034 短保单号；I638 弱",
              "没 Load 到能表达该维的字段/操作符/格式，不得把该维做成 blocking。格式外、称谓、空间外编号：空条件+未识别允许不 NF。OR 多字段若额外分支格式不兼容，不当 extra 收窄。",
              "空间资料过时或没 Load 到时，会把真漏条件当成「空间没有」而 F。少儿万能险丢掉「少儿」若被说成空间表达不了，会放过泛化。I638 若下游 polNo 真吃 C 前缀，会漏掉扩大检索。",
              "对正常「小雨弟弟」友好（关系+性别即可）。对 badcase 里「功能未实现但用户要了」要小心：fulfilled 说职责内没给仍是 NF，不能让空间闸把「本可表达却没给」也赦免。闸门只挡「空间里根本没有的常识扩维」，不挡已登记字段的缺失。",
            ],
            [
              "E. 正常集对照闸，badcase 只做单向约束",
              "防止本轮优化过拟合这 341 条",
              "改任何一条都要同时看：本 xlsx 盘客/漏错/目录三条净胜不回退；另备一截正常姓名+产品+合法单号，F 不得掉。过严 8 条是观察项，不是唯一 KPI。",
              "正常集若也是从 badcase 里挑「看起来像正常」的，仍会偏。真正常流量和标注集分布不同。",
              "这是过程方案，不改判定逻辑。没有它，A–D 都会在这张表上显得很美，上线后姓名/混合问退化看不见。",
            ],
          ]}
        />

        <H3>建议怎么叠，而不是五条一起上</H3>
        <Text>
          推荐顺序：E（先把对照闸立住）→ C（锁住盘客 NF、修 I046/I161，这是 fulfilled 主口径）→ D（挡住常识扩维和格式外强交）→ B 再 A（先消歧再放宽姓名形态，顺序不能反）。
          A 单独上会把共展/见光/金风吐回姓名 F；B 单独上不修王坤林过严；C 单独上不修弟弟/P07；只改 prompt 不加 E，下一轮还会在另一批 badcase 上把正常姓名打回去。
        </Text>
        <Table
          headers={["组合", "过严 8 条", "会吐回的净胜", "正常场景风险"]}
          rows={[
            ["只加 prompt 例外", "部分好转、部分换坑", "高，盘客/合家福可能一起漂", "高，不可控"],
            ["只要 A（形态可 F）", "昊轩/王坤林好转；配/周老板仍乱", "共展/见光/金风 从 NF 变回 F", "姓名召回好，假姓名 F 升"],
            ["C + D，暂不动姓名", "I046/I161、弟弟、P07、周老板、I638", "盘客净胜应能保住", "混合问和弟弟类正常问变稳；姓名过严仍在"],
            ["E + C + D，再 B→A（推荐）", "8 条应对上，且能看见有没有误伤", "盘客/漏错/目录三条可设为不回退", "最低：先锁净胜，再有限度放宽姓名"],
          ]}
          rowTone={["danger", "warning", "info", "success"]}
        />
        <Text size="small" tone="tertiary">
          方案按 fulfilled.md §3.1 / §6 核心聚合、material-positioning 空间/选择分离来划，不是按本 xlsx 准确率最大化来划。
        </Text>
      </Stack>

      <Divider />

      <Stack gap={10}>
        <H3>附表：10 条 live 实质不同（不计入上面 66）</H3>
        <Text tone="secondary">
          同一 user_text，conditions / robot_text 语义不同。I274 已并入同 live。4 条 judge 也不同，但不能归因到 judge。
        </Text>
        <Table
          headers={["ID", "意图", "旧 live", "新 live", "旧/新 judge", "处理"]}
          rows={LIVE_DIFFS}
          striped
        />
      </Stack>

      <Text size="small" tone="tertiary" style={{ color: theme.text.tertiary }}>
        Authority 在 project.yaml 关闭；两边 Judge JSON 都无 authority 字段。因此「盘客/活动」按
        fulfilled §3.1 应是 NF 而不是 NE。若以后打开 Authority 且裁决职责外，这些案应改判说不清，而不是办成了。
      </Text>
    </Stack>
  );
}
